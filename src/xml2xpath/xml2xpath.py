'''Generate xpath expressions from an XML document'''


from collections import OrderedDict
from io import StringIO, BytesIO
from os import path, devnull, strerror
from typing import Dict, List, Tuple, Union
import errno
import sys
import json

from lxml import etree

XPATH_ALL = '//*'
XPATH_REALLY_ALL = f'{XPATH_ALL} | //processing-instruction() | //comment()'
WITH_COUNT = False
MAX_ITEMS = 100000
OUT_FD = sys.stdout
modes = ['xpath', 'all', 'raw', 'values', 'raw_json', 'raw_json_pretty']

def usage():
    helpstr='''
    pyxml2xpath <file path> [mode] [initial xpath expression] [with element count: yes|true] [max elements: int] [no banner: yes|true]
    
    File path: pass '-' to read from stdin
    
    mode: str
        xpath  : print elements xpath expressions (default)
        all   : also print attribute xpath expressions
        raw   : print unqualified xpath and found values (list)
        values: print list of found values only
        raw_json: json string with internal xpath and namespace maps.
                {"xpath": { ... }, "namespaces": { ... }}
        raw_json_pretty: same as raw_json with pretty print
    
    Initial xpath expression: str
        Start at some element defined by an xpath expression.
        //*[local-name()= "act"]
    
    Examples:
        pyxml2xpath tests/resources/soap.xml

        pyxml2xpath tests/resources/HL7.xml none '//*[local-name()= "act"]'
        
        pyxml2xpath tests/resources/HL7.xml 'values' '//*[local-name()= "act"]'
        
        # mode                            : all
        # starting at xpath               : none
        # count elements                  : False
        # Limit elements                  : 11
        # Do not show banner (just xpaths): true
        pyxml2xpath ~/tmp/test.html all none none 11 true
    '''
    print(helpstr)

def _get_qualified_name(qname, revns):
    '''Get qualified name as <prefix>:<local-name>'''
    lname = qname.localname
    if revns.get(qname.namespace) is not None:
        lname = f"{revns.get(qname.namespace)}:{qname.localname}"
    return lname

def get_encoding_from_fragment(xml_frag):
    '''
    Get encoding attribute value from xml declaration if present.
    :param xml_frag: first 100 characters from XML string.
    '''
    declstr = xml_frag.split(b'?>')[0]
    # Fake a minimal doc to parse declaration ensuring encoding is valid for lxml
    frdoc= etree.parse(BytesIO(declstr + b'?><root/>'))
    return frdoc.docinfo.encoding
    
def _get_dict_list_value(value, element):
    '''Initialize tuple for xpath dictionary values.
    Items:
        0) qualified xpath
        1) count of elements found using the latter
        2) list of element's attribute names
    '''
    
    # Add attributes names to current xmap value
    return (value, 0, [*element.keys()])

def _build_path_from_parts(xmap, xp, qname, revns, ele):
    '''Split path on unnamed elements and build qualified xpath
        /soap:root/soap:xpath/*[1]
    could be converted to
        /soap:root/soap:xpath/ns:someelement[1]
    
    Parameters
    ----------
    
    xmap: dict
        xpath expressions dictionary
    xp:   str
        unqualified xpath (source)
    qname: QName
        element's qualfied name object
    revns: dict
        namespace reverse map - URI to prefix.
    ele: etree._ElementTree
        current element'''
    
    parts = [p for p in xp.split("/*")]
    last = parts[0]
    if xp == '/*':
        xmap[xp] = _get_dict_list_value(f"/{_get_qualified_name(qname, revns)}", ele)
    for p in parts[1:]:
        if f'{last}/*{p}' not in xmap:
            xval = f'{xmap.get(last) or ""}/{_get_qualified_name(qname, revns)}'
            xmap[xp] = _get_dict_list_value(xval, ele)
            last = xp
        elif xp[-1] not in ['*', ']']:
            last = xp.split(']/')[0] + ']'
            xval = f'{xmap.get(last) or ""}/{_get_qualified_name(qname, revns)}'
            xmap[xp] = _get_dict_list_value(xval, ele)
        elif f'{last}/*{p}' in xmap:
            last = f'{last}/*{p}'

def parse_mixed_ns(tree: etree._ElementTree,
                   nsmap: Dict,
                   xpath_base: str = XPATH_ALL,
                   *,
                   with_count: bool = WITH_COUNT, 
                   max_items: int = MAX_ITEMS) -> OrderedDict[str, Tuple[str, int, List[str]]]:
    '''Parse XML document that may contain anonymous namespace.
    Returns a dict with original xpath as keys, xpath with qualified names and
    count of elements found with the latter or None if an error occurred.
        xmap = ``{
            "/some/xpath/*[1]": ("/some/xpath/ns:ele1", 1, ["id", "class"])
        }``
    To get the qualified xpath:
        ``xmap['/some/xpath/*[1]'][0]``
    
    :param tree: lxml.etree._ElementTree
        ElementTree from current document
    :param nsmap: dict
        namespaces dictionary from current document
    :param xpath_base: str
        Xpath expression to start from
    :param with_count: bool
        add count of found elements (performance cost on large documents).
    :param max_items: int
        max number of elements to parse. Default: 100000
    '''
    
    revns = {v:k or 'ns' for k,v in nsmap.items()}
    elements = tree.xpath(xpath_base, namespaces=nsmap)

    xmap = None
    try:
        xmap = OrderedDict.fromkeys(map(tree.getpath, elements[:max_items]))
    except TypeError as t:
        if "_ElementUnicodeResult" in t.args[0]:
            print(f"ERROR. Finding xpath expressions for text() nodes is not supported.\nxpath_base: {xpath_base}\nMessage: {t.args[0]}", file=sys. stderr)
        else:
            print(f"ERROR. Unexpected node type error. Please, file a bug.\n{t.args[0]}", file=sys. stderr)
        return None
    except Exception:
        print("ERROR. Unexpected error. Please, file a bug.\n", file=sys. stderr)
        import traceback
        traceback.print_exc()
        return None

    for idx, xp in enumerate(xmap.keys()):
        ele = elements[idx]
        
        if '*' not in xp:
            # xpath expression is already qualified
            # e.g.: /soapenv:Envelope/soapenv:Body
            # or element does not have namespaces
            # e.g.: /root/child
            xmap[xp]= _get_dict_list_value(xp, ele)
        else:
            # Element may contain qualified and unqualified parts
            # /soapenv:Envelope/soapenv:Body/*/*[2]
            # parent may exist even if xpath_base is a relative path: //soapenv:Body
            prnt = ele.getparent()
            if prnt is not None:
                # type(ele): etree._Element
                if type(ele.tag) is str:
                    qname = etree.QName(ele.tag)
                    pqname = etree.QName(prnt.tag)
                    # parent's (unqualified) xpath
                    xpp = tree.getpath(prnt)
                    # parent of current element was already parsed so
                    # just append current qualified name
                    if xpp in xmap:
                        if xmap[xpp] is None:
                            xmap[xpp]= _get_dict_list_value(f"//{_get_qualified_name(pqname, revns)}", ele)
                        xmap[xp] = _get_dict_list_value(f'{xmap[xpp][0]}/{_get_qualified_name(qname, revns)}', ele)
                    else:
                        # element's parent exists but it's not present on xmap.
                        # Adding it as preceding current element but not to xmap.
                        prfx = '//'
                        if prnt == tree.getroot():
                            prfx = '/'
                        xmap[xp] = _get_dict_list_value(f'{prfx}{_get_qualified_name(pqname, revns)}/{_get_qualified_name(qname, revns)}', ele)
                else:
                    # Unqualified xpath support for Comments and processing instructions.
                    # type(ele): etree._Comment or etree._ProcessingInstruction
                    xmap[xp] = xp, 0, None
            else:
                # Probably the first unqualified xpath. Has no parent and is not on xmap yet
                #print(f"DEBUG: Parsing root: {xp}", file=sys. stderr)
                _build_path_from_parts(xmap, xp, etree.QName(ele.tag), revns, ele)
            
        # count elements found with these xpath expressions
        if with_count:
            # Count of elements found with qualified expression
            # Should never be 0.
            #print(f"DEBUG: {xp} {xmap[xp]}", file=sys. stderr)
            xcount = int(tree.xpath(f"count({xmap[xp][0]})", namespaces=nsmap))
            if xcount == 0:
                # no creo en brujas pero que las hay, las hay. xD
                print(f"ERROR: 0 elements found with {xp}. Possibly due to this bug: https://gitlab.gnome.org/GNOME/libxml2/-/issues/715", file=sys. stderr)
                print(f"       element path without parent: {tree.getelementpath(ele)}", file=sys. stderr)
            xmap[xp] = xmap[xp][0], xcount, xmap[xp][2]
    return xmap


def get_json_response(xmap, nsmap, mode):
    '''
    Return a json string as
        {"xpath": { ... }.
        "namespaces": { ... }}
    :param xmap:
    :param nsmap:
    :param mode:
    '''
    indent = None
    raw_json = {}
    raw_json['xpath'] = xmap
    if nsmap:
        raw_json['namespaces'] = nsmap
    if mode == 'raw_json_pretty':
        indent = 4
    return json.dumps(raw_json, indent=indent)

def print_xpaths(xmap: Dict,
                 mode: str ="xpath",
                 *,
                 out_fd = OUT_FD, nsmap= None):
    '''
    Print xpath expressions according to 'mode' argument.
    
    :param xmap: map of xpath expressions
    :param mode: output mode
    :param out_fd: output file descriptor
    :param nsmap: namespaces map
    
    mode: str
        xpath  : print elements xpath expressions (default)
        all   : also print attribute xpath expressions
        raw   : print unqualified xpath and found values (list)
        raw_json: json string with internal xpath and namespace maps.
                {"xpath": { ... }.
                 "namespaces": { ... }}
        raw_json_pretty: same as raw_json with pretty print
        values: print tuple of found values only
    '''
    
    acount=0
    acountmsg=''
    
    if mode in ['raw_json', 'raw_json_pretty']:
        print(get_json_response(xmap, nsmap, mode))
    else:
        for unq_xpath, qual_xpath_lst in xmap.items():
            if mode in ['xpath', 'all']:
                print(qual_xpath_lst[0])
                if mode == "all":
                    #Print xpath for attributes
                    if qual_xpath_lst[2] is not []:
                        for a in qual_xpath_lst[2]:
                            print(f"{qual_xpath_lst[0]}/@{a}")
                            acount += 1
                        acountmsg = f"Found {acount:3} xpath expressions for attributes\n"
            elif mode == "raw":
                print(unq_xpath, qual_xpath_lst)
            elif mode == "values":
                print(qual_xpath_lst)
            
    print(f"\nFound {len(xmap.keys()):3} xpath expressions for elements\n{acountmsg}", file=out_fd)

def build_namespace_dict(tree: etree._ElementTree) ->  Dict[str, str]:
    '''Build a namespaces dictionary with prefix for default namespaces.
    If there are more than 1 default namespace, prefix will be incremental:
    ns98, ns99 and so on.'''
    
    nslst = tree.xpath('//namespace::*[name()!="xml"]')
    nsidx = 98
    ns = f'ns{nsidx}'
    nsmap = {}
    for k, v in nslst:
        if k is not None:
            nsmap[k] = v
            continue
        elif (k is None and v in nsmap.values()) or (k is None and v == ''):
            continue
        elif k is None and ns in nsmap and nsmap[ns] == v:
            continue
        elif k is None and ns in nsmap and nsmap[ns] != v:
            nsidx += 1
            ns = f'ns{nsidx}'
        nsmap[ns] = v
    return nsmap

def fromstring(xmlstr: Union[str,bytes], *,
               xpath_base: str = '//*',
               with_count: bool = WITH_COUNT,
               max_items: int = MAX_ITEMS,
               encoding='utf-8') -> (etree._ElementTree, Dict[str, str], OrderedDict[str, Tuple[str, int, List[str]]]):
    '''
    Parse from string. If the document contains an encoding in XML declaration, use it.
    If it starts with an XML declaration but has no ``encoding`` attribute, ``utf-8`` will be used be default.
    
    :param xmlstr: document or fragment as string or bytes.
    :param xpath_base: xpath expression to start searching xpaths for.
    :param with_count: Include count of elements found with each expression. Default: False
    :param max_items: limit the number of parsed elements. Default: 100000
    :param encoding: xml string encoding, ``utf-8`` by default. Use :func:`get_encoding_from_fragment` to get encoding.
    '''
    xmlbytes = xmlstr
    if isinstance(xmlstr, str):
        xmlbytes = xmlstr.encode(encoding)
    doc = etree.parse(BytesIO(xmlbytes))
    return parse(file=None, itree=doc, xpath_base=xpath_base, with_count=with_count, max_items=max_items)
    
def parse(file: str, *,
          itree: etree._ElementTree = None,
          xpath_base: str = XPATH_ALL,
          with_count: bool = WITH_COUNT,
          max_items: int = MAX_ITEMS) -> (etree._ElementTree, Dict[str, str], OrderedDict[str, Tuple[str, int, List[str]]]):
    '''Parse given xml file, find xpath expressions in it and return
    - The ElementTree for further usage
    - The sanitized namespaces map (no None keys)
    - A dictionary with original xpath as keys, and parsed xpaths, count of elements found with them and names of attributes of that elements:
    
    xmap = {
        "/some/xpath/*[1]": ( "/some/xpath/ns:ele1", 1, ["id", "class"] ),
        "/some/other/xpath/*[3]": ( "/some/other/xpath/ns:other", 1, ["attr1", "attr2"] ),
    }
    
    Parameters
    ----------
        :param file: file path string
        :param itree: lxml.etree._ElementTree
                ElementTree object
        :param xpath_base: xpath expression to start searching xpaths for.
        :param with_count: Include count of elements found with each expression. Default: False
        :param max_items: limit the number of parsed elements. Default: 100000
    '''
    
    try:
        tree = itree
        if tree is None:
            if not path.isfile(file):
                raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), file)
            with open(file, "rb") as fin:
                tree = etree.parse(fin)
        
        nsmap = build_namespace_dict(tree)
        #print(f"Namespaces found: {nsmap}")
        xmap = parse_mixed_ns(tree, nsmap, xpath_base, with_count=with_count, max_items=max_items)
        return (tree, nsmap, xmap)
    except Exception as e:
        print("ERROR.", type(e).__name__, "–", e, file=sys.stderr)
        raise(e)

def main():
    if len(sys.argv) == 1:
        print(f"ERROR: No arguments passed.\nRun with -h for help.", file=sys.stderr)
        sys.exit(1)
    
    if sys.argv[1] in ["-h", "--help"]:
        usage()
        sys.exit()

    file = sys.argv[1]
    mode = "xpath"
    xpath_base = XPATH_ALL
    with_count = WITH_COUNT
    max_items = MAX_ITEMS
    out_fd = OUT_FD
    no_banners = False
    warns = None
    
    if file != '-' and not path.isfile(file):
        print(f"[Errno {errno.ENOENT}] {strerror(errno.ENOENT)}", file=sys.stderr)
        sys.exit(errno.ENOENT)
    
    for i, arg in enumerate(sys.argv):
        if str(arg).lower() in ['', 'none']:
            continue
        
        if i == 2:
            mode = arg
            if mode not in modes:
                print(f"ERROR: {strerror(errno.EINVAL)}.\nUnknown mode: '{mode}'. Must be one of: {modes} or ['', 'none'] to use 'xpath' default mode.", file=sys.stderr)
                sys.exit(errno.EINVAL)
        elif i == 3:
            xpath_base = arg
        elif i == 4 and str(arg).lower() in ['yes', 'true']:
            with_count = True
        elif i == 5:
            max_items = int(arg)
            if max_items > MAX_ITEMS:
                warns = f"WARNING. max_items > {MAX_ITEMS}: {max_items}. It could take a significant time depending on document size."
                if with_count:
                    warns += f"\nWARNING. with_count=True. There's an additional performance cost on getting count of elements if document is big."
        elif i == 6 and str(arg).lower() in ['yes', 'true']:
            # do not print any banner, just xpaths
            no_banners =  True
            out_fd = open(devnull, 'w')

    print(f"Running...\n{'file':10}: {file}", file=out_fd, flush=True)
    print(f"{'mode':10}: {mode}", file=out_fd, flush=True)
    print(f"{'xpath_base':10}: '{xpath_base}'", file=out_fd, flush=True)
    print(f"{'with_count':10}: {with_count}", file=out_fd, flush=True)
    print(f"{'max_items':10}: {max_items}", file=out_fd, flush=True)
    print(f"{'no_banners':10}: {no_banners}", file=out_fd, flush=True)
    if warns is not None:
        print(f"\n{warns}\n", file=sys.stderr)
    if file != '-':
        nsmap, xmap = parse(file,  xpath_base=xpath_base, with_count=with_count, max_items=max_items)[1:]
    else:
        xmlstr = sys.stdin.buffer.read()
        nsmap, xmap = fromstring(xmlstr,  xpath_base=xpath_base, with_count=with_count, max_items=max_items)[1:]
    if xmap is not None:
        print(f"namespaces: {nsmap}\n", file=out_fd, flush=True)
        print_xpaths(xmap, mode, out_fd=out_fd, nsmap=nsmap)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
    
