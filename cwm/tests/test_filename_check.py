import os


def pytest_file_name(directory, suffix="_test.py"):
    """
    Check if files in a directory and its child directories end with a given suffix.
    :param directory: The directory to start the search from.
    :param suffix: The suffix to check for. Default is "_test.py".
    :return: Two lists of files - one with the given suffix and one without.
    """
    files_with_suffix = []
    files_without_suffix = []

    # Traverse the directory and its child directories
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(suffix):
                files_with_suffix.append(os.path.join(root, file))
            else:
                files_without_suffix.append(os.path.join(root, file))

    return files_with_suffix, files_without_suffix


start_directory = (
    "/Users/ndimu/Desktop/rasp/udt-clean-water-toolkit/cwm/tests/cleanwater"
)
files_with_suffix, files_without_suffix = pytest_file_name(start_directory)

print("Files ending with '_test.py':")
for file in files_with_suffix:
    print(file)

print("\nFiles not ending with '_test.py':")
for file in files_without_suffix:
    print(file)
