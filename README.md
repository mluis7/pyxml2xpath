
# pyxml2xpath
Parse XML document and build XPath expression corresponding to its structure.

## Description
Found XPath expressions are tested against the document and the count of found elements is returned. See also `parse()` method below.

## Build and install
```bash
git clone https://github.com/mluis7/pyxml2xpath.git
cd pyxml2xpath
python3.9 -m build
python3.9 -m pip install dist/pyxml2xpath-0.0.3-py3-none-any.whl --upgrade
```
Soon on PyPi!

## Command line usage
`pyxml2xpath <file path> [mode]`

`pyxml2xpath ~/tmp/soap-ws-oasis.xml`

## Module usage

```python
from xml2xpath import xml2xpath
tree, nsmap, xmap = xml2xpath.parse('/home/luis/tmp/wiki.xml')
xml2xpath.print_xpath(xmap, 'all')
```

If an element tree created with `lxml` is available, use it and avoid double parsing the file.

```python
from lxml import etree
from xml2xpath import xml2xpath

doc = etree.parse("/home/luis/tmp/wiki.xml")
tree, nsmap, xmap = xml2xpath.parse(file=None,itree=doc)

```

Result

```
Found xpath for elements

/ns98:feed
/ns98:feed/ns98:id
/ns98:feed/ns98:title
/ns98:feed/ns98:link
/ns98:feed/ns98:link
/ns98:feed/ns98:updated
/ns98:feed/ns98:subtitle
/ns98:feed/ns98:generator
/ns98:feed/ns98:entry
/ns98:feed/ns98:entry/ns98:id
...

Found xpath for attributes

/ns98:feed/@{http://www.w3.org/XML/1998/namespace}lang
/ns98:feed/ns98:link/@rel
/ns98:feed/ns98:link/@type
/ns98:feed/ns98:link/@href
/ns98:feed/ns98:link/@rel
/ns98:feed/ns98:link/@type
/ns98:feed/ns98:link/@href
/ns98:feed/ns98:entry/ns98:link/@rel
...

Found  32 xpath expressions for elements
Found  19 xpath expressions for attributes

```

XPath search could start at a different element than root by passing an xpath expression

```python
xmap = parse(file,  xpath_base='//*[local-name() = "author"]')[2]
```

or

`pyxml2xpath ~/tmp/wiki.xml 'path' '//*[local-name() = "author"]'`

### `parse(file: str, itree: etree._ElementTree = None)` method
Parse given xml file or `lxml` tree, find xpath expressions in it and return:

- The ElementTree for further usage
- The sanitized namespaces map (no None keys)
- A dictionary with original xpath as keys and as values a list of parsed xpaths, count of elements found with them and a dictionary with attributes of that elements:

```python
xmap = {
    "/some/xpath/*[1]": [ 
        "/some/xpath/ns:ele1", 
        1, 
        {"id": "unique"} 
     ],
    "/some/other/xpath/*[3]": [ 
        "/some/other/xpath/ns:other", 
        1, 
        {"name": "myname", "value": "myvalue"} 
     ],
}
```

## Print result modes
Print xpath expressions and validate by count of elements found with it.  

`mode` argument values (optional):

`path` : print elements xpath expressions (default)  
`all`  : also print attribute xpath expressions  

`pyxml2xpath ~/tmp/soap-ws-oasis.xml 'all'`

or if used as module:

`xml2xpath.print_xpath(xmap, 'all')`


## HTML support
HTML has limited support as long as the document is well formed.
