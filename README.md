
# pyxml2xpath
Parse XML document and build XPath expression corresponding to its structure.

<h3> &#x24D8; Project status: BETA </h3>

Table of contents
=================

* [Basic usage](#description)
* [Build and install](#build-and-install)
* [Command line usage](#command-line-usage)
* [Module usage](#module-usage)
* [Method parse(...)](#method-parse)
* [Print result modes](#print-result-modes)
* [HTML support](#html-support)
* [Unqualified vs. Qualified](#unqualified-vs-qualified)
* [Performance](#performance)
* [Known issues](#known-issues)
* [Testing](#testing)

## Description
Iterate elements in XML document and build all existing XPath expression for them.
Also, build qualified expressions from unqualified ones taking into account namespaces:

`tree.getpath(element)  ->  /*/*[9]/*[6]  ->  /ns98:feed/ns98:entry/ns98:author`

```bash
pyxml2xpath tests/resources/simple-no-ns.xml
```
```
Running...
file      : tests/resources/simple-no-ns.xml
mode      : path
xpath_base: '//*'
namespaces: {}

/root
/root/child[1]
/root/child[2]
/root/another

Found   4 xpath expressions for elements
```

A spin off of [xml2xpath Bash script](https://github.com/mluis7/xml2xpath). Both projects rely on [libxml2](https://gitlab.gnome.org/GNOME/libxml2/-/wikis/home) implementation.

## Build and install
```bash
git clone https://github.com/mluis7/pyxml2xpath.git
cd pyxml2xpath
python3.9 -m build
python3.9 -m pip install dist/pyxml2xpath-0.2.0-py3-none-any.whl --upgrade
```

Alternative without cloning the repo yourself

```
pip3.9 install git+https://github.com/mluis7/pyxml2xpath.git
```

Soon on PyPi!

## Command line usage
`pyxml2xpath <file path> [mode] [initial xpath expression]`

```bash
pyxml2xpath tests/resources/soap.xml

pyxml2xpath tests/resources/HL7.xml '' '//*[local-name()= "act"]'

pyxml2xpath tests/resources/HL7.xml 'values' '//*[local-name()= "act"]'

# mode                            : all
# starting at xpath               : none
# count elements                  : False
# Limit elements                  : 11
# Do not show banner (just xpaths): true
pyxml2xpath ~/tmp/test.html all none none 11 true
```


## Module usage

```python
from xml2xpath import xml2xpath
tree, nsmap, xmap = xml2xpath.parse('tests/resources/wiki.xml')
xml2xpath.print_xpath(xmap, 'all')
```

If an element tree created with `lxml` is available, use it and avoid double parsing the file.

```python
from lxml import etree
from xml2xpath import xml2xpath

doc = etree.parse("tests/resources/wiki.xml")
tree, nsmap, xmap = xml2xpath.parse(file=None,itree=doc)

```

Result

```
Found xpath for elements

/ns98:feed
/ns98:feed/ns98:id
/ns98:feed/ns98:title
/ns98:feed/ns98:link
...

Found xpath for attributes

/ns98:feed/@{http://www.w3.org/XML/1998/namespace}lang
/ns98:feed/ns98:link/@rel
/ns98:feed/ns98:link/@type
/ns98:feed/ns98:link/@href
...

Found  32 xpath expressions for elements
Found  19 xpath expressions for attributes

```

XPath search could start at a different element than root by passing an xpath expression

```python
xmap = parse(file,  xpath_base='//*[local-name() = "author"]')[2]
```

or

```
pyxml2xpath tests/resources/HL7.xml '' '//*[local-name()= "act"]'
Running...
file: HL7.xml
mode: path
xpath_base: //*[local-name()= "act"]



//ns98:entry
//ns98:entry/ns98:act
//ns98:entry
//ns98:entry/ns98:act
//ns98:entry
//ns98:entry/ns98:act

Found   6 xpath expressions for elements
```

### Method parse(...)
Signature: `parse(file: str, *, itree: etree._ElementTree = None, xpath_base: str = '//*', with_count: bool = WITH_COUNT, max_items: int = MAX_ITEMS)`

Parse given xml file or `lxml` tree, find xpath expressions in it and return:

- The ElementTree for further usage
- The sanitized namespaces map (no None keys)
- A dictionary with unqualified xpath as keys and as values a tuple of qualified xpaths, count of elements found with them and a list with names of attributes of that elements:

```python
xmap = {
    "/some/xpath/*[1]": (
        "/some/xpath/ns:ele1", 
        1, 
        ["id", "class"] 
     ),
    "/some/other/xpath/*[3]": ( 
        "/some/other/xpath/ns:other", 
        1, 
        ["attr1", "attr2"] 
     ),
}
```

Namespaces dictionary adds a prefix for default namespaces.
If there are more than 1 default namespace, prefix will be incremental:
`ns98`, `ns99` and so on. Try testing file `tests/resources/soap.xml`

**Parameters**

- `file: str` file path string.
- `itree: lxml.etree._ElementTree` ElementTree object.
- `xpath_base: str` xpath expression To start searching xpaths for.
- `with_count: bool` Include count of elements found with each expression. Default: False
- `max_items: int` limit the number of parsed elements. Default: 100000
        
## Print result modes
Print xpath expressions and validate by count of elements found with it.  

`mode` argument values (optional):

- `path`  : print elements xpath expressions (default)  
- `all`   : also print attribute xpath expressions  
- `raw`   : print unqualified xpath and found values (tuple)  
- `values`: print tuple of found values only  

`pyxml2xpath ~/tmp/soap-ws-oasis.xml 'all'`

or if used as module:

`xml2xpath.print_xpath(xmap, 'all')`


## HTML support
HTML has limited support as long as the document or the HTML fragment are well formed. 
Make sure the HTML fragment is surrounded by a single element.
If not, add some fake root element `<root>some_html_fragment</root>`.

See examples on tests:

```
test_01.TestPyXml2Xpath01.test_parse_html
test_01.TestPyXml2Xpath01.test_fromstring_html_fragment
```

```python
from lxml import html
from xml2xpath import xml2xpath

filepath = 'tests/resources/html5-small.html.xml'
hdoc = html.parse(filepath)
xpath_base = '//*[@id="math"]'

xmap = xml2xpath.parse(None, itree=hdoc, xpath_base=xpath_base)[2]
```

or on command line

```
pyxml2xpath tests/resources/html5-small.html.xml 'all' '//*[@id="math"]'
```

```
Running...
file: tests/resources/html5-small.html.xml
mode: all
xpath_base: //*[@id="math"]



//ns98:p
//ns98:p/ns99:math


//ns98:p/ns99:math/@id

Found   2 xpath expressions for elements
Found   1 xpath expressions for attributes
```

## Unqualified vs. Qualified
Symbolic element tree of `tests/resources/wiki.xml` showing position of unqualified elements.

```
feed
  id
  title
  link
  link
  updated
  subtitle
  generator
  entry
    id
    title
    link
    updated
    summary
    author
      name
  entry   <- 9th child of 'feed'
    id
    title
    link
    updated
    summary
    author   <- 6th child of 'entry'
      name
  entry
    id
    title
    link
    updated
    summary
    author
      name
```

`tree.getpath(element)` could return a fully qualified expression, a fully unqualified expression or a mix of both `/soap:Envelope/soap:Body/*[2]`.

Unqualified parts are converted to qualified ones.

```
/*/*[9]/*[6]
/*           # root element
  /*[9]      # 9th child of root element. Tag name unknown.
       /*[6] # 6th child of previous element.  Tag name unknown.
```

qualified expression using appropriate namespace prefix

```
/*/*[9]/*[6]   /ns98:feed/ns98:entry/ns98:author
/*           # /ns98:feed
  /*[9]      #           /ns98:entry
       /*[6] #                      /ns98:author
```

## Performance
Performance degrades quickly for documents that produce more than 500k xpath expressions.  
Measuring timings with `timeit` for main steps in `parsed_mixed_ns()` method it can be seen that most consuming task is initializing the result dictionary while the time taken by `lxml.parse()` method and processing unqualified expressions remains stable.  
An effort was made to remove unnecessary iterations and to optimize dictionary keys preloading so the major penalty remains on the dictionary performance itself.

With times in seconds:

```
tree.xpath: 1.08
dict preloaded with: 750000 keys; 204.20
parse finished: 2.10


tree.xpath: 1.10
dict preloaded with: 1000000 keys; 399.05
parse finished: 2.60
```

Testing file: [Treebank dataset](https://aiweb.cs.washington.edu/research/projects/xmltk/xmldata/) - 82MB uncompressed, 2.4M xpath expressions.

## Known issues
- Count of elements fail with documents with long element names. See [issue pxx-13](https://github.com/mluis7/pyxml2xpath/issues/19)

## Testing
To get some result messages run as

`pytest --capture=no --verbose`

**Verifying found keys**
Compare `xmllint` and `pyxml2xpath` found keys

```bash
printf "%s\n" "setrootns" "whereis //*" "bye" | xmllint --shell resources/HL7.xml | grep -v '^[/] >' > /tmp/HL7-whereis-xmllint.txt
pyxml2xpath resources/HL7.xml 'raw' none none none True | cut -d ' ' -f1 > /tmp/HL7-raw-keys.txt
diff -u /tmp/HL7-raw-keys.txt /tmp/HL7-whereis-xmllint.txt
```
No result returned.

**Verifying found qualified expressions**
Test found xpath qualified expressions with a different tool by counting elements found with them

```bash
#!/bin/bash
xfile='resources/HL7.xml'
cmds=( "setrootns" "setns ns98=urn:hl7-org:v3" )

for xpath in $(pyxml2xpath $xfile none none none none True | sort | uniq); do
    cmds+=( "xpath count($xpath) > 0" )
done

printf "%s\n" "${cmds[@]}" | xmllint --shell "$xfile" | grep -v '^[/] >' | grep -v 'Object is a Boolean : true'

if [ "$?" -ne 0 ]; then
    echo "Success. Counts returned > 0"
fi
```

