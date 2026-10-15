"""Synthetic name and label pools.

Surnames are Hindi/English words meaning "sample", "example", "fictional",
and so on, so every generated person is obviously synthetic. Merchants and
external banks are invented names.
"""

FIRST_NAMES = (
    "Aarav", "Aditi", "Akash", "Ananya", "Arjun", "Asha", "Bhavna", "Chetan", "Deepa", "Dev",
    "Divya", "Farhan", "Gauri", "Harsh", "Ishaan", "Jaya", "Kabir", "Kavya", "Lakshmi", "Manav",
    "Meera", "Mohan", "Naina", "Neel", "Nisha", "Omkar", "Pooja", "Pranav", "Rahul", "Ritu",
    "Rohan", "Sana", "Sameer", "Shreya", "Siddharth", "Simran", "Tanvi", "Tarun", "Uma", "Varun",
    "Vidya", "Vikram", "Yash", "Zoya", "Anil", "Kiran", "Sunita", "Ravi", "Geeta", "Imran",
)

SURNAMES = (
    "Kalpanik", "Namuna", "Udaharan", "Nakli", "Sampleton", "Demowala", "Parikshan", "Kaalpanik",
    "Fictiva", "Testani", "Mockwal", "Dummykar",
)

MERCHANTS_UPI = (
    "Chai Point Example", "Kirana Demo Store", "Sabzi Sample Mart", "Auto Fare (synthetic)",
    "Example Mobile Recharge", "Demo Electricity Board", "Sample Pharmacy", "Fictional Dhaba",
    "Mock Milk Dairy", "Example Gas Agency",
)

MERCHANTS_POS = (
    "Demo Supermart", "Example Fashion House", "Sample Electronics", "Mock Fuel Station",
    "Fictional Book Depot", "Example Restaurant", "Demo Hardware", "Sample Shoe Store",
)

EXTERNAL_BANKS = ("Example Co-operative Bank", "Demo Gramin Bank", "Sample Urban Bank")

STAFF = tuple(f"Staff-{i:02d}" for i in range(1, 16))
