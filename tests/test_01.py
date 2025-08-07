import glob
from xml2xpath import xml2xpath
from lxml import html

class TestPyXml2Xpath01:
    def test_all_samples_basic(self):
        sample_paths = glob.glob('resources/*.xml')
        xpath_base = "//*"
        print("")
        for xfile in sample_paths:
            print(f"Testing '{xfile}'")
            xmap = xml2xpath.parse(xfile,  xpath_base=xpath_base, with_count=True)[2]
            print(f"    --> Found {len(xmap.keys())} xpath expressions")
            assert len(xmap.keys()) > 0
            # assert all found expressions exist at least once in the document.
            # all expressions found at least 1 element
            assert len([v for v in xmap.values() if v[1] == 0]) == 0
    
    def test_parse_with_initial_xpath(self):
        filepath = 'resources/soap.xml'
        xpath_base = '//*[local-name()="incident"]'
        print(f"\nTesting '{filepath}' starting at: '{xpath_base}'")
        
        nsmap, xmap = xml2xpath.parse(filepath, xpath_base=xpath_base, with_count=True)[1:]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        print(f"    --> Found {len(nsmap.keys())} namespaces")
        print(f"    --> nsmap: {nsmap}")
        # do not count parent element
        assert len([k for k in xmap if k != '/soap:Envelope/soap:Body' ]) == 1
        # assert all found expressions exist at least once in the document.
        assert len([v for v in xmap.values() if v[1] == 0]) == 0
        assert len(nsmap.keys()) == 3
    
    def test_fromstring(self):
        '''
        Read file as string instead of bytes.
        '''
        filepath = 'resources/iso-8859-1.xml'
        with open(filepath,'r', encoding='iso-8859-1') as fd:
            xmlstr = fd.read()
            print(f"\nTesting fromstring() from '{filepath}', type: {type(xmlstr)}")
            
            nsmap, xmap = xml2xpath.fromstring(xmlstr, with_count=True, encoding='iso-8859-1')[1:]
            print(f"    --> Found {len(xmap.keys())} xpath expressions")
            print(f"    --> Found {len(nsmap.keys())} namespaces")
            print(f"    --> nsmap: {nsmap}")
            # do not count parent element
            assert len(xmap.keys()) == 3
            # assert all found expressions exist at least once in the document.
            assert len([v for v in xmap.values() if v[1] == 0]) == 0

    def test_fromstring_and_xpath_base(self):
        filepath = 'resources/soap.xml'
        with open(filepath, 'rb') as fd:
            xmlstr = fd.read()
            xpath_base = '//*[local-name()="incident"]'
            print(f"\nTesting fromstring() from '{filepath}' starting at: '{xpath_base}'")
        
            nsmap, xmap = xml2xpath.fromstring(xmlstr,  xpath_base=xpath_base, with_count=True)[1:]
            print(f"    --> Found {len(xmap.keys())} xpath expressions")
            print(f"    --> Found {len(nsmap.keys())} namespaces")
            print(f"    --> nsmap: {nsmap}")
            # do not count parent element
            assert len([k for k in xmap if k != '/soap:Envelope/soap:Body' ]) == 1
            # assert all found expressions exist at least once in the document.
            assert len([v for v in xmap.values() if v[1] == 0]) == 0
            assert len(nsmap.keys()) == 3
    
    def test_parse_html(self):
        filepath = 'resources/html5-small.html.xml'
        hdoc = html.parse(filepath)
        xpath_base = '//*[@id="math"]'
        print(f"\nTesting HTML at '{filepath}' starting at: '{xpath_base}'")
    
        xmap = xml2xpath.parse(None, itree=hdoc, xpath_base=xpath_base)[2]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        # do not count parent element
        assert len([k for k in xmap if k != '//ns98:p' ]) == 1
    
    def test_fromstring_html_fragment(self):
        filepath = 'resources/html5-small.html.xml'
        xpath_base = '//*[@id="math"]'
        # generate html fragment string for testing
        hdoc = html.parse(filepath)
        html_frag_orig = hdoc.getroot().xpath(xpath_base)[0]
        html_frag = f"<root>{html.tostring(html_frag_orig).decode('utf-8')}</root>"
        
        print(f"\nTesting HTML fragment starting at: '{xpath_base}'")
    
        xmap = xml2xpath.fromstring(html_frag.encode('utf-8'))[2]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        assert len(xmap) == 14
    
    def test_parse_processing_instruction_initial_xpath(self):
        filepath = 'resources/simple-ns.xml'
        xpath_base = '//processing-instruction("pitest")[preceding-sibling::comment()]'
        print(f"\nTesting '{filepath}' starting at: '{xpath_base}'")
        
        nsmap, xmap = xml2xpath.parse(filepath, xpath_base=xpath_base, with_count=True)[1:]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        print(f"    --> Found {len(nsmap.keys())} namespaces")
        print(f"    --> nsmap: {nsmap}")
        
        assert len([v for v in xmap.values() if v[1] == 0]) == 0
        assert len(xmap.keys()) == 1, "1 processing-instruction found"
    
    def test_parse_get_everything(self):
        filepath = 'resources/simple-anon-ns.xml'
        xpath_base = xml2xpath.XPATH_REALLY_ALL
        print(f"\nTesting '{filepath}' starting at: '{xpath_base}'")
        
        nsmap, xmap = xml2xpath.parse(filepath, xpath_base=xpath_base, with_count=True)[1:]
        print(f"    --> Found {len(xmap.keys())} xpath expressions")
        print(f"    --> Found {len(nsmap.keys())} namespaces")
        print(f"    --> nsmap: {nsmap}")
        
        assert len([v for v in xmap.values() if v[1] == 0]) == 0
        assert len(xmap.keys()) == 11
        assert len([k for k in xmap.keys() if "comment()" in k]) == 2
        assert len([k for k in xmap.keys() if "processing-instruction(" in k]) == 2
    
    def test_compare_order(self):
        '''Triggered by
        https://stackoverflow.com/questions/78321064/how-to-compare-xml-layout-with-a-xml-fiscal-note-with-python/78324167#78324167
        '''
        xmap = xml2xpath.parse('resources/simple-ns.xml')[2]
        # same elements but different order
        xmap2 = xml2xpath.parse('resources/simple-ns-rev-order.xml')[2]
        
        assert xmap != xmap2

