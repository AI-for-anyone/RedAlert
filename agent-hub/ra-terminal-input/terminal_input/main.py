import argparse
import os
import pyarrow as pa
from dora import Node
from mofa.utils.install_pkg.load_task_weaver_result import extract_important_content
RUNNER_CI = True if os.getenv("CI") == "true" else False

def clean_string(input_string:str):
    return input_string.encode('utf-8', 'replace').decode('utf-8')
def send_task_and_receive_data(node):
    TIMEOUT = 300
    while True:
        data = input(
            " Send Your Task :  ",
        )
        print(f"data=={data}")
        if data == "/bye" or data == "/BYE":
            print("end")
            return
        node.send_output("data", pa.array([clean_string(data)]))
        
def main():

    node = Node("ra-terminal-input")  # provide the name to connect to the dataflow if dynamic node
    send_task_and_receive_data(node)

if __name__ == "__main__":
    main()