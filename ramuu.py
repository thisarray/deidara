"""Script to summarize RAM prices."""

import datetime
import decimal
import json
import re
import statistics
import unittest

_SIZE_PRICE_PATTERN = re.compile(r"""^(?P<count>\d)x
(?P<size>\d+)GB@[$]
(?P<price>[0-9.]+)""", re.ASCII | re.VERBOSE)
"""Regular expression pattern to parse the memory module information."""

class Item:
    def __init__(self, date, dimm_type, store, size, price, brand):
        """Initialize an Item instance."""
        if not isinstance(date, datetime.date):
            raise TypeError('date must be a datetime.date.')
        if not isinstance(dimm_type, str):
            raise TypeError('dimm_type must be a string.')
        if not isinstance(store, str):
            raise TypeError('store must be a string.')
        if not isinstance(size, int):
            raise TypeError('size must be a positive integer.')
        if size <= 0:
            raise ValueError('size must be a positive integer.')
        if not isinstance(price, decimal.Decimal):
            raise TypeError('price must be a decimal.Decimal.')
        if not isinstance(brand, str):
            raise TypeError('brand must be a string.')

        self.date = date
        """datetime.date the price was collected."""

        self.dimm_type = dimm_type
        """String type of the RAM module(s)."""

        self.store = store
        """String name of the store selling this item."""

        self.size = size
        """Integer total size of the RAM module(s)."""

        self.price = price
        """decimal.Decimal price on self.date."""

        self.brand = brand
        """String brand of the manufacturer."""

    def __str__(self):
        return '{}GB {} @ ${} from {} on {}'.format(
            self.size, self.dimm_type, self.price, self.store,
            self.date.isoformat())


def _parse_description(description):
    """Return the size, the price, and the brand from description.

    Args:
        description: String description in the form "2x8GB@$19.99 Brand".
    Returns:
        Integer total number of GB
        decimal.Decimal price
        String brand
    """
    if not isinstance(description, str):
        raise TypeError('description must be a non-empty string.')
    if len(description) < 10:
        raise ValueError('description must be a non-empty string.')

    part, separator, brand = description.partition(' ')
    if len(separator) <= 0:
        return 0, decimal.Decimal(), brand

    if part[1] != 'x':
        part = '1x' + part

    match = _SIZE_PRICE_PATTERN.search(part)
    if match is None:
        return 0, decimal.Decimal(), brand

    try:
        count = int(match.group('count'))
    except ValueError:
        count = 0
    try:
        size = int(match.group('size')) * count
    except ValueError:
        size = 0

    price = decimal.Decimal(match.group('price'))

    return size, price, brand

def _parse_module_size(description):
    """Return a string size of the memory module in description.

    >>> _parse_module_size('4GB')
    '4'
    >>> _parse_module_size('8 GB')
    '8'
    >>> _parse_module_size('16GB (2x8GB)')
    '2x8'
    >>> _parse_module_size('(2 x 8GB) 16GB')
    '2x8'

    Args:
        description: String description of a RAM module.
    Returns:
        String size of the memory module in description.
    """
    if not isinstance(description, str):
        raise TypeError('description must be a string.')

    sizes = []
    end = -1
    while True:
        end = description.find('GB', end + 1)
        if end <= 0:
            break
        start = end - 1
        # Skip any space between the size and "GB"
        while (start >= 0) and description[start].isspace():
            start -= 1
        # Move to the start of the size
        while (start >= 0) and description[start].isdigit():
            start -= 1
        start += 1
        try:
            sizes.append(int(description[start:end].strip()))
        except ValueError:
            pass

    if len(sizes) <= 0:
        return None
    if len(sizes) == 1:
        return str(sizes[0])
    else:
        if sizes[0] == sizes[1]:
            return str(sizes[0])
        else:
            numerator = max(*sizes[:2])
            denominator = min(*sizes[:2])
            return '{}x{}'.format(numerator // denominator, denominator)

def _parse_micro_center(source):
    """Parse and print the micro center webpage in source.

    Args:
        source: String source of the micro center webpage.
    Returns:
        List of float price and string description tuples.
    """
    if not isinstance(source, str):
        raise TypeError('source must be a string.')

    start = source.find('<div id="productImpressions" class="hidden">')
    end = source.find('</div>', start + 44)
    products = json.loads('[' + source[start+44:end].replace("'", '"') + ']')
    if not isinstance(products, list):
        return []

    descriptions = []
    for product in products:
        if not isinstance(product, dict):
            continue
        size = _parse_module_size(product.get('name'))
        if not isinstance(size, str):
            continue
        price = product.get('price')
        size += 'GB@${} {}'.format(price, product.get('brand'))
        descriptions.append((decimal.Decimal(price.replace(',', '')), size))

    if len(descriptions) > 0:
        print('        micro center:')
        descriptions.sort()
        for price, description in descriptions:
            print('        -', description)

    return descriptions

def _parse_newegg(source):
    """Parse and print the titles in the Newegg feed in source.

    Args:
        source: String source of the Newegg feed.
    Returns:
        List of float price and string description tuples.
    """
    if not isinstance(source, str):
        raise TypeError('source must be a string.')

    descriptions = []
    start = -1
    while True:
        start = source.find('<title>', start + 1)
        if start <= 0:
            break
        end = source.find('</title>', start + 7)
        title = source[start+7:end].strip()
        if not title.startswith('&#36;'):
            continue

        title = title[5:]
        size = _parse_module_size(title)
        if not isinstance(size, str):
            continue
        separator = title.find(' - ')
        price = title[:separator]
        brand_end = separator + 3
        while not title[brand_end].isspace():
            brand_end += 1
        brand = title[separator+3:brand_end].strip()
        size += 'GB@${} {}'.format(price, brand)
        descriptions.append((decimal.Decimal(price.replace(',', '')), size))

    if len(descriptions) > 0:
        print('        Newegg:')
        descriptions.sort()
        for price, description in descriptions:
            print('        -', description)

    return descriptions

def _parse_document(document):
    """Return a list of Item instances parsed from the dictionary document.

    Args:
        document: Dictionary containing price descriptions.
    Returns:
        List of Item instances parsed from document.
    """
    if not isinstance(document, dict):
        return []

    result = []
    for date in document:
        if (isinstance(date, datetime.date) and
            isinstance(document[date], dict)):
            for dimm_type in document[date]:
                if isinstance(document[date][dimm_type], dict):
                    for store in document[date][dimm_type]:
                        if isinstance(document[date][dimm_type][store], list):
                            for entry in document[date][dimm_type][store]:
                                size, price, brand = _parse_description(entry)
                                if size > 0:
                                    result.append(Item(date, dimm_type, store,
                                                       size, price, brand))
    return result


class _UnitTest(unittest.TestCase):
    def test_pattern(self):
        """Test the regular expression pattern."""
        for value in ['', 'foobar', __doc__]:
            self.assertIsNone(_SIZE_PRICE_PATTERN.search(value))
        for value, expected in [
            ('1x4GB@$14.99', ('1', '4', '14.99')),
            ('1x4GB@$14.99 ', ('1', '4', '14.99')),
            ('1x4GB@$14.99 Foo', ('1', '4', '14.99')),
            ('1x8GB@$18.99', ('1', '8', '18.99')),
            ('1x8GB@$18.99 ', ('1', '8', '18.99')),
            ('1x8GB@$18.99 Foo', ('1', '8', '18.99')),
            ('2x4GB@$24.99', ('2', '4', '24.99')),
            ('2x4GB@$24.99 ', ('2', '4', '24.99')),
            ('2x4GB@$24.99 Foo', ('2', '4', '24.99')),
            ('2x8GB@$28.99', ('2', '8', '28.99')),
            ('2x8GB@$28.99 ', ('2', '8', '28.99')),
            ('2x8GB@$28.99 Foo', ('2', '8', '28.99')),
            ('4x4GB@$44.99', ('4', '4', '44.99')),
            ('4x4GB@$44.99 ', ('4', '4', '44.99')),
            ('4x4GB@$44.99 Foo', ('4', '4', '44.99')),
            ('4x8GB@$48.99', ('4', '8', '48.99')),
            ('4x8GB@$48.99 ', ('4', '8', '48.99')),
            ('4x8GB@$48.99 Foo', ('4', '8', '48.99'))]:
            self.assertEqual(_SIZE_PRICE_PATTERN.findall(value), [expected])

    def test_parse_description(self):
        """Test parsing the string description."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_description, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertRaises(ValueError, _parse_description, value)
        for value, expected in [
            ('1x4GB@$14.99', (0, decimal.Decimal(), '')),
            ('1x4GB@$14.99 ', (4, decimal.Decimal('14.99'), '')),
            ('1x4GB@$14.99 Foo', (4, decimal.Decimal('14.99'), 'Foo')),
            ('1x8GB@$18.99', (0, decimal.Decimal(), '')),
            ('1x8GB@$18.99 ', (8, decimal.Decimal('18.99'), '')),
            ('1x8GB@$18.99 Foo', (8, decimal.Decimal('18.99'), 'Foo')),
            ('2x4GB@$24.99', (0, decimal.Decimal(), '')),
            ('2x4GB@$24.99 ', (8, decimal.Decimal('24.99'), '')),
            ('2x4GB@$24.99 Foo', (8, decimal.Decimal('24.99'), 'Foo')),
            ('2x8GB@$28.99', (0, decimal.Decimal(), '')),
            ('2x8GB@$28.99 ', (16, decimal.Decimal('28.99'), '')),
            ('2x8GB@$28.99 Foo', (16, decimal.Decimal('28.99'), 'Foo')),
            ('4x4GB@$44.99', (0, decimal.Decimal(), '')),
            ('4x4GB@$44.99 ', (16, decimal.Decimal('44.99'), '')),
            ('4x4GB@$44.99 Foo', (16, decimal.Decimal('44.99'), 'Foo')),
            ('4x8GB@$48.99', (0, decimal.Decimal(), '')),
            ('4x8GB@$48.99 ', (32, decimal.Decimal('48.99'), '')),
            ('4x8GB@$48.99 Foo', (32, decimal.Decimal('48.99'), 'Foo'))]:
            self.assertEqual(_parse_description(value), expected)

    def test_parse_module_size(self):
        """Test parsing a memory module's size."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_module_size, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertIsNone(_parse_module_size(value))
        for value, expected in [
            (' 4GB', '4'),
            (' 4 GB', '4'),
            ('8GB', '8'),
            ('8 GB', '8'),
            ('16GB ', '16'),
            ('16 GB ', '16'),
            ('16GB (2x8GB)', '2x8'),
            ('16GB (2x 8GB)', '2x8'),
            ('16GB (2x8 GB)', '2x8'),
            ('16GB (2x 8 GB)', '2x8'),
            ('16GB (2 x8GB)', '2x8'),
            ('16GB (2 x 8GB)', '2x8'),
            ('16GB (2 x8 GB)', '2x8'),
            ('16GB (2 x 8 GB)', '2x8'),
            ('16 GB (2x8GB)', '2x8'),
            ('16 GB (2x 8GB)', '2x8'),
            ('16 GB (2x8 GB)', '2x8'),
            ('16 GB (2x 8 GB)', '2x8'),
            ('16 GB (2 x8GB)', '2x8'),
            ('16 GB (2 x 8GB)', '2x8'),
            ('16 GB (2 x8 GB)', '2x8'),
            ('16 GB (2 x 8 GB)', '2x8'),
            ('(2x8GB) 16GB', '2x8'),
            ('(2x 8GB) 16GB', '2x8'),
            ('(2x8 GB) 16GB', '2x8'),
            ('(2x 8 GB) 16GB', '2x8'),
            ('(2 x8GB) 16GB', '2x8'),
            ('(2 x 8GB) 16GB', '2x8'),
            ('(2 x8 GB) 16GB', '2x8'),
            ('(2 x 8 GB) 16GB', '2x8'),
            ('(2x8GB) 16 GB', '2x8'),
            ('(2x 8GB) 16 GB', '2x8'),
            ('(2x8 GB) 16 GB', '2x8'),
            ('(2x 8 GB) 16 GB', '2x8'),
            ('(2 x8GB) 16 GB', '2x8'),
            ('(2 x 8GB) 16 GB', '2x8'),
            ('(2 x8 GB) 16 GB', '2x8'),
            ('(2 x 8 GB) 16 GB', '2x8'),
            # Test misleading numbers preceding the size
            ('4 8GB', '8'),
            ('4 8 GB', '8'),
            ('4 16GB (2x8GB)', '2x8'),
            ('4 16GB (2x 8GB)', '2x8'),
            ('4 16GB (2 x 8GB)', '2x8'),
            ('4 16GB (2 x 8 GB)', '2x8'),
            ('4 16 GB (2x8GB)', '2x8'),
            ('4 16 GB (2x 8GB)', '2x8'),
            ('4 16 GB (2 x 8GB)', '2x8'),
            ('4 16 GB (2 x 8 GB)', '2x8')]:
            self.assertEqual(_parse_module_size(value), expected)
            self.assertEqual(_parse_module_size('Foobar ' + value), expected)
            self.assertEqual(_parse_module_size(value + ' baz'), expected)
            self.assertEqual(_parse_module_size('Foobar ' + value + ' baz'),
                             expected)
            if '(' in value:
                self.assertEqual(_parse_module_size(value.replace('(', '( ')),
                                 expected)
                self.assertEqual(_parse_module_size(value.replace(')', ' )')),
                                 expected)

    def test_parse_micro_center(self):
        """Test parsing the micro center webpage."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_micro_center, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertEqual(_parse_micro_center(value), [])
        self.assertEqual(_parse_micro_center('''
<div id="productImpressions" class="hidden">{
'name': 'Foobar 4GB',
'brand': 'Foobar',
'price': '14.99'}, {
'name': 'Foobar 8GB (2 x 4GB)',
'brand': 'Foobar',
'price': '24.99'}, {
'name': 'Foobar 8GB',
'brand': 'Foobar',
'price': '18.99'}, {
'name': 'Foobar 16GB (2 x 8GB)',
'brand': 'Foobar',
'price': '28.99'}
</div>
'''), [(decimal.Decimal('14.99'), '4GB@$14.99 Foobar'),
       (decimal.Decimal('18.99'), '8GB@$18.99 Foobar'),
       (decimal.Decimal('24.99'), '2x4GB@$24.99 Foobar'),
       (decimal.Decimal('28.99'), '2x8GB@$28.99 Foobar')])

    def test_parse_newegg(self):
        """Test parsing the Newegg feed."""
        for value in [None, 42.0, []]:
            self.assertRaises(TypeError, _parse_newegg, value)
        for value in ['', 'foobar', 'foobarbaz']:
            self.assertEqual(_parse_newegg(value), [])
        self.assertEqual(_parse_newegg('''<rss version="2.0">
<title>&#36;14.99 - Foobar 4GB</title>
<title>&#36;24.99 - Foobar 8GB (2 x 4GB)</title>
<title>&#36;18.99 - Foobar 8GB</title>
<title>&#36;28.99 - Foobar 16GB (2 x 8GB)</title>
</rss>
'''), [(decimal.Decimal('14.99'), '4GB@$14.99 Foobar'),
       (decimal.Decimal('18.99'), '8GB@$18.99 Foobar'),
       (decimal.Decimal('24.99'), '2x4GB@$24.99 Foobar'),
       (decimal.Decimal('28.99'), '2x8GB@$28.99 Foobar')])

    def test_item(self):
        """Test the Item class."""
        today = datetime.datetime.now(datetime.timezone.utc).date()
        for value in [None, 42.0, []]:
            self.assertRaises(
                TypeError, Item, value, '', '', 1, decimal.Decimal(), '')
            self.assertRaises(
                TypeError, Item, today, value, '', 1, decimal.Decimal(), '')
            self.assertRaises(
                TypeError, Item, today, '', value, 1, decimal.Decimal(), '')
            self.assertRaises(
                TypeError, Item, today, '', '', value, decimal.Decimal(), '')
            self.assertRaises(
                TypeError, Item, today, '', '', 1, value, '')
            self.assertRaises(
                TypeError, Item, today, '', '', 1, decimal.Decimal(), value)
        for value in [-1, 0]:
            self.assertRaises(
                ValueError, Item, today, '', '', value, decimal.Decimal(), '')

    def test_parse_document(self):
        """Test parsing a YAML document."""
        for value in [None, 42.0, [], {}, {'foo': 'bar'}]:
            self.assertEqual(_parse_document(value), [])

if __name__ == '__main__':
    import argparse
    import doctest
    import os.path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-m', '--microcenter', default=[], nargs='+',
        help='fetch, parse, and print the micro center pages at URLs')
    parser.add_argument(
        '-n', '--newegg', default=[], nargs='+',
        help='fetch, parse, and print the Newegg feeds at URLs')
    parser.add_argument(
        '-p', '--path', default='',
        help='parse the YAML price data at path')
    parser.add_argument(
        '-s', '--store', default='',
        help='string name of the store on which to filter')
    parser.add_argument(
        '-t', '--type', default='',
        help='string type of the module on which to filter')
    args = parser.parse_args()

    if len(args.microcenter) > 0:
        import requests
        with requests.Session() as session:
            for url in args.microcenter:
                response = session.get(url)
                _parse_micro_center(response.text)
    elif len(args.newegg) > 0:
        import requests
        with requests.Session() as session:
            for url in args.newegg:
                response = session.get(url)
                _parse_newegg(response.text)
    elif os.path.isfile(args.path):
        import yaml
        items = []
        with open(args.path, 'r', encoding='utf-8') as f:
            for document in yaml.safe_load_all(f):
                items.extend(_parse_document(document))
        if len(args.store) > 0:
            items = [item for item in items if item.store == args.store]
        if len(args.type) > 0:
            items = [item for item in items if item.dimm_type == args.type]
        for item in items:
            print(item)
        if len(items) > 0:
            print('Price/GB: ${}'.format(statistics.mean(
                [item.price / item.size for item in items])))
    else:
        tests = [doctest.DocTestSuite(),
                 unittest.defaultTestLoader.loadTestsFromTestCase(_UnitTest)]
        unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(tests))
