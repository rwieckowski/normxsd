import argparse
from pathlib import Path
from typing import Callable, Generator
import xml.etree.ElementTree as ET


def parse_args(args=None):
    parser = argparse.ArgumentParser(description="Normalize XML schema")
    parser.add_argument("-i", "--input", type=Path, default=Path.cwd(),
                        help="Input file or directory")
    parser.add_argument("-o", "--output", type=Path,
                        help="Output file or directory", required=True)
    parser.add_argument('-r', '--recursive', action='store_true')
    parsed_args = parser.parse_args(args)

    input_path: Path = parsed_args.input.absolute()
    output_path: Path = parsed_args.output.absolute()
    if input_path == output_path:
        parser.error("Input and output must not be the same")
    if input_path.is_file() and output_path.is_dir() \
            and input_path.parent == output_path:
        parser.error("Input and output must not be in the same directory")

    return parsed_args


def loadxml(filename: str) -> ET.Element:
    tree = ET.parse(filename)
    return tree.getroot()


def savexml(element: ET.Element, filename: str):
    tree = ET.ElementTree(element)
    tree.write(filename, encoding="utf-8", xml_declaration=True)


Transformation = Callable[[ET.Element], ET.Element]


def transform_tree(transformations: list[Transformation],
                   element: ET.Element) -> ET.Element:
    for transformation in transformations:
        element = transformation(element)

    for child in element:
        transform_tree(transformations, child)

    return element


def remove_annotations(element: ET.Element) -> ET.Element:
    annotations = element.findall(
        '{http://www.w3.org/2001/XMLSchema}annotation')

    for annotation in annotations:
        element.remove(annotation)

    return element


def strip_text(element: ET.Element) -> ET.Element:
    if element.text:
        element.text = element.text.strip()

    return element


SORTABLE_ELEMENTS = [
    "{http://www.w3.org/2001/XMLSchema}all",
    "{http://www.w3.org/2001/XMLSchema}choice",
    "{http://www.w3.org/2001/XMLSchema}sequence",
]


def sort_elements_by_name_attr(element: ET.Element) -> ET.Element:
    if element.tag in SORTABLE_ELEMENTS:
        element[:] = sorted(element, key=lambda e: e.get('name', default=''))

    return element


def sort_attributes(element):
    attrs = element.attrib
    if attrs:
        attrs = sorted(attrs.items())
        element.attrib.clear()
        element.attrib.update(attrs)
    return element


def sort_elements_by_tag_name(element: ET.Element) -> ET.Element:
    element[:] = sorted(element, key=lambda e: e.tag)
    return element


def format_tree(element: ET.Element) -> ET.Element:
    ET.indent(element, space=' ' * 2, level=0)
    return element


def iterfiles(path: Path, recursive: bool = True) -> Generator[Path, None, None]:
    if path.is_file():
        yield path
    if path.is_dir():
        for f in path.iterdir():
            if f.is_file() and f.suffix == '.xsd':
                yield f
            if f.is_dir() and recursive:
                yield from iterfiles(f, recursive)


def outputfile(input_path: Path, output_path: Path, input_file: Path) -> Path:
    if input_path.is_file() and output_path.is_dir():
        return output_path / input_file.name

    if input_path.is_file():
        return output_path

    return output_path / input_file.relative_to(input_path)


def transform(input_file: str, output_file: str):
    transformations = [remove_annotations, strip_text,
                       sort_elements_by_name_attr, sort_attributes]

    root = loadxml(input_file)
    root = transform_tree(transformations, root)
    root = sort_elements_by_tag_name(root)
    root = format_tree(root)
    savexml(root, output_file)


def main():
    args = parse_args()
    for input_file in iterfiles(args.input, args.recursive):
        if input_file.is_relative_to(args.output):
            print('Skipping', input_file)
            continue

        output_file = outputfile(args.input, args.output, input_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(input_file, '->', output_file)
        transform(str(input_file), str(output_file))


if __name__ == '__main__':
    main()
