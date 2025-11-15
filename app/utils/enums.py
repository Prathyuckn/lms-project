from enum import Enum


class LibraryItemTypes(Enum):
    BOOK = "book"
    EBOOK = "ebook"
    DVD = "dvd"


class LibraryItemAvailabilityType(Enum):
    PHYSICAL = "Physical"
    DIGITAL = "Digital"


class ItemCopyStatus(Enum):
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    AT_OTHER_BRANCH = "at_other_branch"
    IN_TRANSIT = "in_transit"
    DELETED = "deleted"


class MemberStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    BLOCKED = "blocked"
    DELETED = "deleted"


class TransactionType(Enum):
    BORROW = "borrow"
    RETURN = "return"


class TransferStatus(Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"


class BorrowedItemStatus(Enum):
    IN_HAND = "in_hand"
    RETURNED = "returned"
