import requests
import sqlite3
import json
import tree_sitter_python as tspython
from tree_sitter import Language, Parser



class ParseService:

    def __init__(self) -> None:
        PY_LANGUAGE = Language(tspython.language())
        self.parser = Parser(PY_LANGUAGE)
        self.conn = sqlite3.connect('data.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS python_files
                            (file_name TEXT PRIMARY KEY,
                             function_name TEXT,
                             class_name TEXT,
                             function_code TEXT,
                             identifiers TEXT)''')
        self.conn.commit()

        

    def extract_info_from_python_file(self, file_content):

        tree = self.parser.parse(bytes(file_content, 'utf-8'))


        identifiers = []
        function_info = []


        cursor = tree.walk()

        def traverse_tree(cursor):
            node = cursor.node
            if node.type == "identifier":
                identifiers.append(node)

            if node.type == "function_definition":
                function_name_node = node.child_by_field_name('name')
                function_name = file_content[function_name_node.start_byte:function_name_node.end_byte]
                class_name = None


                parent_node = node.parent
                if parent_node and parent_node.type == "class_definition":
                    class_name_node = parent_node.child_by_field_name('name')
                    class_name = file_content[class_name_node.start_byte:class_name_node.end_byte]


                function_identifiers = []
                for child in node.children:
                    if child.type == "identifier":
                        identifier = file_content[child.start_byte:child.end_byte]
                        function_identifiers.append(identifier)


                function_code = file_content[node.start_byte:node.end_byte]

                function_info.append({
                    "function_name": function_name,
                    "class_name": class_name,
                    "function_code": function_code,
                    "identifiers": function_identifiers
                })


            if cursor.goto_first_child():
                while True:
                    traverse_tree(cursor)
                    if not cursor.goto_next_sibling():
                        break
                cursor.goto_parent()


        traverse_tree(cursor)

        return function_info

    def fetch_python_files_from_github(self, repo_url):
        parts = repo_url.strip("/").split("/")
        username, repo_name = parts[-2], parts[-1]

        root_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/"
        response = requests.get(root_url)
        response.raise_for_status()
        contents = response.json()

        python_files = {}

        def fetch_files_recursively(contents, path=""):
            for item in contents:
                if item["type"] == "file" and item["name"].endswith(".py"):
                    python_files[path + item["name"]] = item["download_url"]
                elif item["type"] == "dir":
                    subdir_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{item['path']}"
                    subdir_response = requests.get(subdir_url)
                    subdir_response.raise_for_status()
                    subdir_contents = subdir_response.json()
                    fetch_files_recursively(subdir_contents, path + item["name"] + "/")

        fetch_files_recursively(contents)

        return python_files

    def fetch_file_content(self, file_url):
        response = requests.get(file_url)
        response.raise_for_status()
        return response.text

    def get_files(self, github_url):
        python_files = self.fetch_python_files_from_github(github_url)
        res = {}
        print("Content of Python files found in the repository:")
        for file_name, file_url in python_files.items():
            content = self.fetch_file_content(file_url)
            print(f"File: {file_name}\n{content}\n")
            function_info = self.extract_info_from_python_file(content)
            res[file_name]=function_info
            for info in function_info:
                self.cursor.execute('''INSERT OR REPLACE INTO python_files
                                    (file_name, function_name, class_name, function_code, identifiers)
                                    VALUES (?, ?, ?, ?, ?)''',
                                    (file_name, info['function_name'], info['class_name'],
                                    info['function_code'], json.dumps(info['identifiers'])))
                self.conn.commit()

        return res


# Example usage
def main(githubUrl):
    github = ParseService()
    res = github.get_files(githubUrl)
    return res
