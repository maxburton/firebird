phone_number = "01234"
if phone_number[0] != "0" and phone_number[0] in "0123456789":
    phone_number = "0" + phone_number
print(phone_number)