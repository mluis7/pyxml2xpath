'''Find all xpath expressions on XML document'''

from collections import OrderedDict
import errno
from io import StringIO
from os import path, devnull, strerror
import sys
from typing import Dict, List, Tuple

from lxml import etree

XPATH_ALL = '//*'
WITH_COUNT = False
MAX_ITEMS = 100000
OUT_FD = sys.stdout

def usage():
    helpstr='''
    pyxml2xpath <file path> [mode] [initial xpath expression] [with element count: yes|true] [max elements: int] [no banner: yes|true]
    
    mode: str
        path  : print elements xpath expressions (default)
        all   : also print attribute xpath expressions
        raw   : print unqualified xpath and found values (list)
        values: print list of found values only
    
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

def get_qname(qname, revns):
    '''Get qualified name'''
    lname = qname.localname
    if revns.get(qname.namespace) is not None:
        lname = f"{revns.get(qname.namespace)}:{qname.localname}"
    return lname

def get_dict_list_value(value, element):
    '''Initialize tuple for xpath dictionary values.
    Items:
        0) qualified xpath
        1) count of elements found using the latter
        2) list of element's attribute names
    '''
    
    # Add attributes names to current xmap value
    if element is not None and element.attrib is not None:
        return (value, 0, element.attrib.keys())
    return (value, 0, [])

def build_path_from_parts(xmap, xp, qname, revns, ele):
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
        namespace reverse map - URI to prefix.'''
    
    parts = [p for p in xp.split("/*")]
    last = parts[0]
    for p in parts[1:]:
        if f'{last}/*{p}' not in xmap:
            xval = f'{xmap.get(last) or ""}/{get_qname(qname, revns)}'
            xmap[xp] = get_dict_list_value(xval, ele)
            last = xp
        elif xp[-1] not in ['*', ']']:
            last = xp.split(']/')[0] + ']'
            xval = f'{xmap.get(last) or ""}/{get_qname(qname, revns)}'
            xmap[xp] = get_dict_list_value(xval, ele)
        elif f'{last}/*{p}' in xmap:
            last = f'{last}/*{p}'

def parse_mixed_ns(tree: etree._ElementTree, nsmap: Dict, xpath_base: str = XPATH_ALL, *, with_count: bool = WITH_COUNT, max_items: int = MAX_ITEMS) -> OrderedDict[str, Tuple[str, int, List[str]]]:
    '''Parse XML document that may contain anonymous namespace.
    Returns a dict with original xpath as keys, xpath with qualified names and count of elements found with the latter.
        xmap = {
            "/some/xpath/*[1]": ("/some/xpath/ns:ele1", 1, ["id", "class"])
        }
    To get the qualified xpath:
        xmap['/some/xpath/*[1]'][0]
        
    Parameters
    ----------
    tree: lxml.etree._ElementTree
        ElementTree from current document
    nsmap: dict
        namespaces dictionary from current document'''
    
    revns = {v:k or 'ns' for k,v in nsmap.items()}
    elements = tree.xpath(xpath_base, namespaces=nsmap)
    xmap = OrderedDict()
    for ele in elements[:max_items]:
        xp = tree.getpath(ele)
        #print(f"DEBUG: {xp}", file=sys. stderr)
        if xp in xmap:
            # Do not update an existing element. Should not enter here, but ...
            print(f"ERROR: duplicated path: {xp}",file=sys. stderr)
            continue

        qname = etree.QName(ele.tag)
        if '*' not in xp:
            # xpath expression is already qualified
            # e.g.:
            #        /soapenv:Envelope/soapenv:Body
            # or element does not have namespaces
            # e.g.:
            #        /root/child
            xmap[xp]= get_dict_list_value(xp, ele)
        else:
            # Element may contain qualified and unqualified parts
            # /soapenv:Envelope/soapenv:Body/*/*[2]
            # parent may exist even if xpath_base is a relative path: //soapenv:Body
            prnt = ele.getparent()
            if prnt is not None:
                pqname = etree.QName(prnt.tag)
                # parent's (unqualified) xpath
                xpp = tree.getpath(prnt)
                # parent of current element was already parsed so just append current qualified name
                if xpp in xmap:
                    xmap[xp] = get_dict_list_value(f'{xmap[xpp][0]}/{get_qname(qname, revns)}', ele)
                else:
                    # element's parent exists but it's not present on xmap.
                    # Adding it and then adding current element.
                    xmap[xpp]= get_dict_list_value(f"//{get_qname(pqname, revns)}", ele)
                    xmap[xp] = get_dict_list_value(f'{xmap[xpp][0]}/{get_qname(qname, revns)}', ele)
            else:
                # Probably the first unqualified xpath. Has no parent and is not on xmap yet
                #print(f"DEBUG: Parsing root: {xp}", file=sys. stderr)
                build_path_from_parts(xmap, xp, qname, revns, ele)
        
        # Add attributes names to current xmap value
        if ele.attrib is not None:
            xmap[xp][2].extend(ele.attrib.keys())
            
    # count elements found with these xpath expressions
    if with_count:
        for k, v in xmap.items():
            # Define a nodeset with qualified expression: (/ns98:feed/ns98:entry/ns98:author)
            # and get the first element or none defined by the count of unqualified expression: count(/*/*[9]/*[6])
            # (/ns98:feed/ns98:entry/ns98:author)[count(/*/*[9]/*[6])]
            # for example: count((author author author)[1])
            # the count of that will be 1 and it means both expressions were validated to return results.
            xmap[k]= v[0], int(tree.xpath(f"count(({v[0]})[count({k})])", namespaces=nsmap)), v[2]
    return xmap

def print_xpaths(xmap: Dict, mode: str ="path", *, with_count: bool = WITH_COUNT, out_fd = OUT_FD):
    '''Print xpath expressions and validate by count of elements found with it.
    mode: str
        path  : print elements xpath expressions (default)
        all   : also print attribute xpath expressions
        raw   : print unqualified xpath and found values (list)
        values: print tuple of found values only
    '''
    
    acount=0
    acountmsg=''
    
    if mode in ["path", "all"]:
        for unq_xpath, qxpath_lst in xmap.items():
                print(qxpath_lst[0])
                if qxpath_lst[1] <= 0 and with_count:
                    # built xpath didn't find elements
                    print(f"ERROR: {int(qxpath_lst[1])} elements found with {qxpath_lst[0]} xpath expression.\nOriginal xpath: {unq_xpath}", file=sys.stderr)
    
    if mode == "all":
        #Print xpath for attributes
        for unq_xpath, qxpath_lst in xmap.items():
            if qxpath_lst[2] is None:
                continue
            #if qxpath_lst[1] > 0:
            for a in qxpath_lst[2]:
                print(f"{qxpath_lst[0]}/@{a}")
                acount += 1
        acountmsg = f"Found {acount:3} xpath expressions for attributes\n"
    elif mode == "raw":
        for key, value in xmap.items():
            print(key, value)
    elif mode == "values":
        for key, value in xmap.items():
            print(value)
                
    print(f"\nFound {len(xmap.keys()):3} xpath expressions for elements\n{acountmsg}", file=out_fd)

def build_namespace_dict(tree):
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

def fromstring(xmlstr: str, *, xpath_base: str = '//*', with_count: bool = WITH_COUNT, max_items: int = MAX_ITEMS) -> (etree._ElementTree, Dict[str, str], OrderedDict[str, Tuple[str, int, List[str]]]):
    doc = etree.parse(StringIO(xmlstr))
    return parse(file=None, itree=doc, xpath_base=xpath_base, with_count=with_count, max_items=max_items)
    
def parse(file: str, *, itree: etree._ElementTree = None, xpath_base: str = '//*', with_count: bool = WITH_COUNT, max_items: int = MAX_ITEMS) -> (etree._ElementTree, Dict[str, str], OrderedDict[str, Tuple[str, int, List[str]]]):
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
        file: file path string
        itree: lxml.etree._ElementTree
                ElementTree object
        xpath_base: xpath expression so start searching xpaths for.
        with_count: Include count of elements found with each expression. Default: False
        max_items: limit the number of parsed elements. Default: 100000
    '''
    
    try:
        tree = itree
        if tree is None:
            if not path.isfile(file):
                raise FileNotFoundError(errno.ENOENT, strerror(errno.ENOENT), file)
            with open(file, "r") as fin:
                tree = etree.parse(fin)
        
        nsmap = build_namespace_dict(tree)
        #print(f"Namespaces found: {nsmap}")
        xmap = parse_mixed_ns(tree, nsmap, xpath_base, with_count=with_count, max_items=max_items)
        return (tree, nsmap, xmap)
    except Exception as e:
        print("ERROR.", type(e).__name__, "–", e, file=sys.stderr)
        raise(e)

def main():
    if sys.argv[1] in ["-h", "--help"]:
        usage()
        sys.exit()

    file = sys.argv[1]
    mode = "path"
    xpath_base = "//*"
    with_count = WITH_COUNT
    max_items = MAX_ITEMS
    out_fd = OUT_FD
    
    if not path.isfile(file):
        print(f"[Errno {errno.ENOENT}] {strerror(errno.ENOENT)}", file=sys.stderr)
        sys.exit(errno.ENOENT)
    
    for i, arg in enumerate(sys.argv):
        if str(arg).lower() in ['', 'none']:
            continue
        
        if i == 2:
            mode = arg
        elif i == 3:
            xpath_base = arg
        elif i == 4 and str(arg).lower() in ['yes', 'true']:
            with_count = True
        elif i == 5:
            max_items = int(arg)
        elif i == 6 and str(arg).lower() in ['yes', 'true']:
            out_fd = open(devnull, 'w')

    print(f"Running...\n{'file':10}: {file}\n{'mode':10}: {mode}\n{'xpath_base':10}: '{xpath_base}'\n{'with_count':10}: {with_count}\n{'max_items':10}: {max_items}", file=out_fd, flush=True)
    nsmap, xmap = parse(file,  xpath_base=xpath_base, with_count=with_count, max_items=max_items)[1:]
    print(f"namespaces: {nsmap}\n", file=out_fd, flush=True)
    print_xpaths(xmap, mode, out_fd=out_fd)

if __name__ == "__main__":
    main()
    
