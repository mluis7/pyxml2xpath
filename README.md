
# pyxml2xpath
Parse an XML document with [lxml](https://lxml.de/) and build XPath expressions corresponding to its structure.

Table of contents
=================

* [Basic usage](#description)
* [Installation](#installation)
* [Command line usage](#command-line-usage)
* [Module usage](#module-usage)
* [Method parse(...)](#method-parse)
* [Print result modes](#print-result-modes)
* [HTML support](#html-support)
* [Relative expressions](#relative-expressions)
* [Unqualified vs. Qualified](#unqualified-vs-qualified)
* [Initial Xpath Examples](#initial-xpath-examples)
* [Performance](#performance)
* [Known issues](#known-issues)
* [Testing](#testing)

## Description
Iterates elements in a XML document and builds XPath expression for them starting at root element by default or at an element defined by an xpath expression.  
Xpath expressions returned by `lxml` are converted to fully qualified ones taking into account namespaces if they exist.  

Source expression could have qualified and unqualified parts with unknown element names  
`/soapenv:Envelope/soapenv:Body/*/*[5]/*[2]`  

A qualified one is returned  
`/soapenv:Envelope/soapenv:Body/ns98:requestMessage/ns98:item/ns98:quantity`  

Supported node types on path: elements, comments and processing instructions

`//* | //processing-instruction() | //comment()`  

text node types can be used in predicates but not on path

|  Xpath                                | Supported |
| :------------------------------------ |:---------:|
| //element[text() = "some text"]       | Yes       |
| //element/text()                      | No        |

It can be used as a [command line utility](#command-line-usage) or as a [module](#module-usage).

> A spin off of [xml2xpath Bash script](https://github.com/mluis7/xml2xpath). Both projects rely on [libxml2](https://gitlab.gnome.org/GNOME/libxml2/-/wikis/home) implementation.

## Installation
Installing from PyPi

`pip3.12 install pyxml2xpath`

Or building from source repo

```bash
git clone https://github.com/mluis7/pyxml2xpath.git
cd pyxml2xpath
python3.12 -m build
python3.12 -m pip install dist/pyxml2xpath-0.2.0-py3-none-any.whl --upgrade
```

Alternative without cloning the repo yourself

```
pip3.12 install git+https://github.com/mluis7/pyxml2xpath.git
```

## Command line usage
`pyxml2xpath <file path> [mode] [initial xpath expression] [with count] [max elements] [without banners]`

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
Reading from stdin pass `-` as file

```bash
cat tests/resources/simple-ns.xml | pyxml2xpath - xpath none false 100 false

pyxml2xpath - xpath none false 100 false < tests/resources/simple-ns.xml
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

### Method parse(...)
Signature: `parse(file: str, *, itree: etree._ElementTree = None, xpath_base: str = '//*', with_count: bool = WITH_COUNT, max_items: int = MAX_ITEMS)`

Parse given xml file or `lxml` tree, find xpath expressions in it and return:

- The ElementTree for further usage
- The sanitized namespaces map (no None keys)
- A dictionary with unqualified xpath as keys and as values a tuple of qualified xpaths, count of elements found with them (optional) and a list with names of attributes of that elements.  
  Returns `None` if an error occurred.

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

**mode** argument values (optional):

| Mode | Description |
| ---- | ----------- |
| `xpath` | print elements xpath expressions (default) |
| `all` | also print attribute xpath expressions |
| `raw` | print unqualified xpath and found values (tuple) |
| `values` | print tuple of found values only |
| `raw_json` | json string with internal xpath and namespace maps. |
| `raw_json_pretty` | same as raw_json with pretty print |

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

## Relative expressions
Build relative expressions when passing `xpath_base` kword argument. The xpath of the parent should be removed so `base_xpath` should be like:

`xpath_base = '//*[@id="math"]/parent::* | //*[@id="math"]/descendant-or-self::*'`

Example:

```python
from lxml import html
from xml2xpath import xml2xpath

filepath = 'tests/resources/html5-small.html.xml'
hdoc = html.parse(filepath)

needle = 'math'
xpath_base = f'//*[@id="{needle}"]/parent::* | //*[@id="{needle}"]/descendant-or-self::*'
xmap = xml2xpath.parse(None, itree=hdoc, xpath_base=xpath_base)[2]

rel_xpath = []
xiter = iter(xmap)
# parent xpath
x0 = next(xiter)
# base element xpath
x1 = next(xiter)
# get base element attributes and build a predicate with first
x1a = ''
if len(xmap[x1][2]) > 0:
    x1a = f'[@{xmap[x1][2][0]}="{needle}"]'
# base element relative xpath (/html/body/math -> //math)
x1f = x1.replace(x0, '/')
# remove numeric indexes if any (div[1] -> div)
x1f = x1f.split('[', 1)[0]
# add first attribute as predicate
x1f += x1a
rel_xpath.append(x1f)

# children relative xpath
for xs in list(xmap.keys())[2:]:
    rel_xpath.append(xs.replace(x1, x1f))

for x in rel_xpath:
    print(x)
```

Output

```None
//math[@id='math']
//math[@id='math']/mrow
//math[@id='math']/mrow/mi
//math[@id='math']/mrow/mo
//math[@id='math']/mrow/mfrac
//math[@id='math']/mrow/mfrac/mn
//math[@id='math']/mrow/mfrac/msqrt
//math[@id='math']/mrow/mfrac/msqrt/mrow
//math[@id='math']/mrow/mfrac/msqrt/mrow/msup
//math[@id='math']/mrow/mfrac/msqrt/mrow/msup/mi
//math[@id='math']/mrow/mfrac/msqrt/mrow/msup/mn
//math[@id='math']/mrow/mfrac/msqrt/mrow/mo
//math[@id='math']/mrow/mfrac/msqrt/mrow/mn
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

## Initial Xpath Examples
To use with 3rd command line argument or `xpath_base` named parameter.

```
# Elements, comments and PIs
//* | //processing-instruction() | //comment()
/descendant-or-self::node()[not(.=self::text())]

# A processing instruction with a comment preceding sibling
//processing-instruction("pitest")[preceding-sibling::comment()]

# Comment following a ns98:typeId element
//comment()[preceding-sibling::ns98:typeId[parent::ns98:ClinicalDocument]][1]

# A comment containing specified text.
//comment()[contains(., "before root")]
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
- Count of elements fails with documents with long element names. See [issue pxx-13](https://github.com/mluis7/pyxml2xpath/issues/19)

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

