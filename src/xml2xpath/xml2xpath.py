'''Find all xpath expressions on XML document'''

import sys
from lxml import etree
from typing import Dict, Tuple

def get_qname(qname, revns):
    '''Get qualified name'''
    lname = qname.localname
    if revns.get(qname.namespace) is not None:
        lname = f"{revns.get(qname.namespace)}:{qname.localname}"
    return lname

def get_dict_list_value(value):
    '''Initialize list for xpath dictionary values.
    Items:
        0) qualified xpath
        1) count of elements found using the latter
        2) dictionary of element attributes
    '''
    return [value, None, None]

def build_path_from_parts(xmap, xp, qname, revns):
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
            xmap[xp] = get_dict_list_value(xval)
            last = xp
        elif xp[-1] not in ['*', ']']:
            last = xp.split(']/')[0] + ']'
            xval = f'{xmap.get(last) or ""}/{get_qname(qname, revns)}'
            xmap[xp] = get_dict_list_value(xval)
        elif f'{last}/*{p}' in xmap:
            last = f'{last}/*{p}'

def parse_mixed_ns(tree: etree._ElementTree, nsmap: Dict) -> Dict:
    '''Parse XML document that may contain anonymous namespace.
    Returns a dict with original xpath as keys, xpath with qualified names and count of elements found with the latter.
        xmap = {
            "/some/xpath/*[1]": ["/some/xpath/ns:ele1", 1, {"id": "unique"}]
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
    elst = tree.xpath('//*', namespaces=nsmap)
    xmap = {}
    for ele in elst:
        xp = tree.getpath(ele)
        qname = etree.QName(ele.tag)
        if xp in xmap:
            # Do not update an existing element. Should not enter here, but ...
            print(f"ERROR: duplicated path: {xp}",file=sys. stderr)
            continue
        if '*' not in xp:
            # xpath expression is already qualified
            # e.g.:
            #        /soapenv:Envelope/soapenv:Body
            # or element does not have namespaces
            # e.g.:
            #        /root/child
            xmap[xp]= get_dict_list_value(xp)
            continue
        else:
            # Element may contain qualified and unqualified parts
            # /soapenv:Envelope/soapenv:Body/*/*[2]
            prnt = ele.getparent()
            if prnt is not None:
                # parent's (unqualified) xpath
                xpp = tree.getpath(prnt)
                # parent of current element was already parsed so just append current qualified name
                if xpp in xmap:
                    xmap[xp] = get_dict_list_value(f'{xmap[xpp][0]}/{get_qname(qname, revns)}')
            else:
                # Probably the first unqualified xpath. Has no parent and is not on xmap yet
                build_path_from_parts(xmap, xp, qname, revns)
        
        # Add attributes to current xmap value
        xmap[xp][2] = ele.attrib
            
    # count elements found with these xpath expressions
    for k, v in xmap.items():
        xmap[k][1] = tree.xpath(f"count({v[0]})", namespaces=nsmap)
    return xmap

def print_xpaths(xmap: Dict, mode: str ="path"):
    '''Print xpath expressions and validate by count of elements found with it.
    mode: str
        path : print elements xpath expressions
        all  : also print attribute xpath expressions'''
    if mode != "none":
        print("\nFound xpath for elements\n")
    
    for unq_xpath, qxpath_lst in xmap.items():
        if qxpath_lst[1] > 0 and mode != "none":
            print(qxpath_lst[0])
        elif qxpath_lst[1] <= 0:
            # built xpath didn't find elements
            print(f"ERROR: {int(qxpath_lst[1])} elements found with {qxpath_lst[0]} xpath expression.\nOriginal xpath: {unq_xpath}", file=sys. stderr)
    
    acount=0
    acountmsg=''
    if mode == "all":
        print("\nFound xpath for attributes\n")
        #Print xpath for attributes
        for unq_xpath, qxpath_lst in xmap.items():
            if qxpath_lst[2] is None:
                continue
            if qxpath_lst[1] > 0:
                for a in qxpath_lst[2]:
                    print(f"{qxpath_lst[0]}/@{a}")
                    acount += 1
        acountmsg = f"Found {acount:3} xpath expressions for attributes\n"
                
    print(f"\nFound {len(xmap.keys()):3} xpath expressions for elements\n{acountmsg}")

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

def parse(file: str, itree: etree._ElementTree = None) -> (etree._ElementTree, Dict[str, str], Tuple[str, int, Dict[str, str]]):
    '''Parse given xml file, find xpath expressions in it and return
    - The ElementTree for further usage
    - The sanitized namespaces map (no None keys)
    - A dictionary with original xpath as keys, and parsed xpaths, count of elements found with them and attributes of that elements:
    
    xmap = {
        "/some/xpath/*[1]": [ "/some/xpath/ns:ele1", 1, {"id": "unique"} ],
        "/some/other/xpath/*[3]": [ "/some/other/xpath/ns:other", 1, {"name": "myname", "value": "myvalue"} ],
    }
    '''
    
    try:
        tree = itree
        if tree is None:
            with open(file, "r") as fin:
                tree = etree.parse(fin)
        nsmap = build_namespace_dict(tree)
        #print(f"Namespaces found: {nsmap}")
        xmap = parse_mixed_ns(tree, nsmap)
        return (tree, nsmap, xmap)
    except Exception as e:
        sys.exit(f"Error parsing {file}: {e}\n")

def main():
    file = sys.argv[1]
    mode = "path"
    
    if len(sys.argv) > 2:
        mode = sys.argv[2]
    
    print(f"Running...\nfile: {file}\nmode: {mode}")
    xmap = parse(file)[2]
    print_xpaths(xmap, mode)

if __name__ == "__main__":
    main()
    