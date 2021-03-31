from typing import List


def from_txt_to_list(txt_path: str) -> List[str]:
    """
    Get a list of string from a txt, one element per line
    :param txt_path: path to txt file
    :return: List of str, one per file row
    """
    rows = []
    with open(txt_path) as open_txt:
        for line in open_txt:
            if line.strip():
                rows.append(line.strip())
    return rows