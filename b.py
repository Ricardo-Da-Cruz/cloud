import json

def save_list_to_file(my_list, filename):
    with open(filename, 'w') as file:
        json.dump(my_list, file)
    print(f'List saved to {filename}')

def read_list_from_file(filename):
    with open(filename, 'r') as file:
        my_list = json.load(file)
    print(f'List read from {filename}')
    return my_list

# Example usage
my_list = [1, 2, 3, 4, 5]
save_list_to_file(my_list, 'my_list.json')

loaded_list = read_list_from_file('my_list.json')
print(loaded_list)