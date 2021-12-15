from typing import List


class Experience:
    def __init__(self, exp_id: str, title: str, substances_details: list, story: List[str],
                 substances_simple: List[str], metadata: dict, tags: List[dict]):
        self.exp_id: str = exp_id
        self.title: str = title
        self.substances_details: list = substances_details
        self.story: List[str] = story
        self.substances_simple: List[str] = substances_simple
        self.metadata: dict = metadata
        self.tags: List[dict] = tags
