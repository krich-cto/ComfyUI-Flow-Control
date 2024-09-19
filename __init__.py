from .functions_validate_nodes import flow_control_validate
from .node_mappings import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS, WEB_DIRECTORY

import execution # type: ignore

node_count = len(NODE_CLASS_MAPPINGS)

print("------------------------------------------")    
print("\033[34mFlow Control v1.00 : \033[92m {0} Nodes Loaded\033[0m".format(node_count))
print("------------------------------------------") 

execution.validate_prompt = flow_control_validate

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']