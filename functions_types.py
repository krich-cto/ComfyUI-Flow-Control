class AnyType(str):
    """A special class that is always equal in comparisons. Credit to crystian & pythongosssss"""

    def __eq__(self, _) -> bool:
        return True

    def __ne__(self, __value: object) -> bool:
        return False