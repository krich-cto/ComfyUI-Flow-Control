from typing import Union
import execution # type: ignore
import nodes # type: ignore

original_validate = execution.validate_prompt

def get_condition_nodes(prompt:dict) -> dict:
    '''Find the Unique ID of the nodes'''
    node_ids = dict()

    for node_id, node_data in prompt.items():
        if node_data["class_type"] == "FlowClipCondition":
            node_ids[node_id] = "base"
        elif node_data["class_type"] == "FlowImageCondition":
            node_ids[node_id] = "image"
        elif node_data["class_type"] == "FlowLatentCondition":
            node_ids[node_id] = "latent"

    return node_ids

def is_flexible_inputs(node_data:dict, condition_node_class_type:str) -> bool:
    if node_data['class_type'] == 'FlowConditioningAutoSwitch' and condition_node_class_type == "FlowClipCondition":
        return True
    if node_data['class_type'] == 'FlowImageAutoBatch' and condition_node_class_type == "FlowImageCondition":
        return True
    if node_data['class_type'] == 'FlowLatentAutoBatch' and condition_node_class_type == "FlowLatentCondition":
        return True
    
    return False

def remove_uncondition_nodes(prompt:dict, condition_node_id:str, condition_node_input_id:str, conditions:dict) -> dict:
    '''"Delete nodes that do not meet the conditions'''
    condition_node_class_type = prompt[condition_node_id]['class_type']
    condition_node_name = "#" + condition_node_id + " " + condition_node_class_type

    print(f"[Flow Control] {condition_node_name} - Conditions : {conditions}")
    print(f"[Flow Control] {condition_node_name} - Prompt : prompt[condition_node_id]")

    try:
        input_node_id, input_node_output_index = prompt[condition_node_id]['inputs'][condition_node_input_id]
        input_node_name = "#" + input_node_id + " " + prompt[input_node_id]['class_type']
    except KeyError:
        print(f"[Flow Control] {condition_node_name} : Not connected.")
        return prompt

    input_node_class = nodes.NODE_CLASS_MAPPINGS[prompt[input_node_id]['class_type']]
    input_node_output_type = str(input_node_class.RETURN_TYPES[input_node_output_index]).lower().strip()

    if condition_node_class_type == "FlowClipCondition":
        gates_node_id, _ = prompt[condition_node_id]['inputs']['base']
        gates_node_name = "#" + gates_node_id + " " + prompt[gates_node_id]['class_type']

        gates_node_values = []
        gates_node_output = 'Single'
        gates_node_values.append("SD15")
        gates_node_values.append("SDXL")

        print(f"[Flow Control] {condition_node_name} - Input {input_node_name} : Output Type = {input_node_output_type}")
        print(f"[Flow Control] {condition_node_name} - Gates {gates_node_name} : Values = {gates_node_values}")
    else:
        gates_node_id, _ = prompt[condition_node_id]['inputs']['gates']
        gates_node_name = "#" + gates_node_id + " " + prompt[gates_node_id]['class_type']
        
        gates_node_output = ""
        gates_node_values = []
        for gates_node_input_key, gates_node_input_value in prompt[gates_node_id]['inputs'].items():
            if gates_node_input_key == "output":
                gates_node_output = gates_node_input_value.strip()
            elif gates_node_input_key.startswith("gate_"):
                trim_value = gates_node_input_value.strip()
                if len(trim_value) > 0:
                    gates_node_values.append(trim_value)

        print(f"[Flow Control] {condition_node_name} - Input {input_node_name} : Output Type = {input_node_output_type}")
        print(f"[Flow Control] {condition_node_name} - Gates {gates_node_name} : Output = {gates_node_output}, Values = {gates_node_values}")
    
    uncondition_node_ids = []
    gate_opened_indices = []
    if gates_node_output == "Single":
        key = next(iter(conditions))
        if type(conditions[key]) is bool:
            if (conditions[key] == True):
                gate_opened_indices.append(0)
            else:
                gate_opened_indices.append(1)
        elif type(conditions[key]) is str:
            try:
                value_index = gates_node_values.index(conditions[key])
                gate_opened_indices.append(value_index)
            except:
                print(f"[Flow Control] {condition_node_name} - Condition : [{conditions[key]}] not found.")
    elif gates_node_output == "Multiple":
        for condition, on_off in conditions.items():
            try:
                value_index = gates_node_values.index(condition)
                if on_off == True:
                    gate_opened_indices.append(value_index)
            except:
                print(f"[Flow Control] {condition_node_name} - Condition : [{condition}] not found.")

    for node_id, node_data in prompt.items():
        node_name = "#" + node_id + " " + prompt[node_id]['class_type']
        uncondition_input_ids = []
        node_flexible_inputs = is_flexible_inputs(node_data, condition_node_class_type)

        for node_input_id, node_input_value in node_data["inputs"].items():
            if not isinstance(node_input_value, list):
                continue

            linked_node_id = node_input_value[0]
            linked_node_output_index = node_input_value[1]

            if condition_node_id == linked_node_id:
                # target_node_name = "#" + node_id + " " + prompt[node_id]['class_type']
                # target_node_class = nodes.NODE_CLASS_MAPPINGS[node_data['class_type']]
                # target_node_input_type = (target_node_class.INPUT_TYPES()['required'][node_input_key][0]).lower().strip()
    
                # print(condition_node_name, "- Target", target_node_name, ": Input Type =", target_node_input_type, ", Linked =", node_input_value)

                # if image_node_output_type != "*" and target_node_input_type != "*" and image_node_output_type != target_node_input_type:
                #     raise IOError()
                
                # Remove input on AutoBatch node
                if node_flexible_inputs and linked_node_output_index not in gate_opened_indices:
                    uncondition_input_ids.append(node_input_id)
                    continue

                if linked_node_output_index not in gate_opened_indices:
                    uncondition_node_ids.append(node_id)
                    break

        for node_input_id in uncondition_input_ids:
            input_name = node_name + "[" + node_input_id + "]"
            print(f"[Flow Control] {condition_node_name} - Delete Input : {input_name}")
            del node_data["inputs"][node_input_id]

        # If there is no input on the AutoBatch node, remove the node..
        if node_flexible_inputs and (not node_data["inputs"].items()):
            uncondition_node_ids.append(node_id)

    for node_id in uncondition_node_ids:
        node_name = "#" + node_id + " " + prompt[node_id]['class_type']
        print(f"[Flow Control] {condition_node_name} - Delete Node : {node_name}")
        del prompt[node_id]

    if len(uncondition_node_ids) > 0:
        return remove_uncondition_children_nodes(prompt, condition_node_id, uncondition_node_ids)
    else:
        return prompt

def remove_uncondition_children_nodes(prompt:dict, condition_node_id:str, removed_node_ids:list) -> dict:
    '''Delete the subsequent nodes of which source has been deleted'''
    condition_node_class_type = prompt[condition_node_id]['class_type']
    condition_node_name = "#" + condition_node_id + " " + condition_node_class_type
    uncondition_children_node_ids = []

    for node_id, node_data in prompt.items():
        node_name = "#" + node_id + " " + prompt[node_id]['class_type']
        uncondition_input_ids = []
        node_flexible_inputs = is_flexible_inputs(node_data, condition_node_class_type)

        for node_input_id, node_input_value in node_data["inputs"].items():
            # Connection is always a List
            if not isinstance(node_input_value, list):
                continue

            # Remove input on AutoBatch node
            if node_flexible_inputs and any(ID in node_input_value for ID in removed_node_ids):
                uncondition_input_ids.append(node_input_id)
                continue

            if any(ID in node_input_value for ID in removed_node_ids):
                uncondition_children_node_ids.append(node_id)
                break

        for node_input_id in uncondition_input_ids:
            input_name = node_name + "[" + node_input_id + "]"
            print(f"[Flow Control] {condition_node_name} - Delete Input : {input_name}")
            del node_data["inputs"][node_input_id]

        # If there is no input on the AutoBatch node, remove the node..
        if node_flexible_inputs and (not node_data["inputs"].items()):
            uncondition_children_node_ids.append(node_id)

    for node_id in uncondition_children_node_ids:
        node_name = "#" + node_id + " " + prompt[node_id]['class_type']
        print(f"[Flow Control] {condition_node_name} - Delete Node : {node_name}")
        del prompt[node_id]

    if len(uncondition_children_node_ids) > 0:
        return remove_uncondition_children_nodes(prompt, condition_node_id, uncondition_children_node_ids)
    else:
        return prompt
    
def flow_control_validate(prompt_id, prompt, partial_execution_list: Union[list[str], None]):
    condition_nodes = get_condition_nodes(prompt)

    if len(condition_nodes) == 0:
        return original_validate(prompt_id, prompt, partial_execution_list)

    print(f"[Flow Control] Prompt Node Ids : {prompt.keys()}")
    print(f"[Flow Control] Condition Node Ids : {condition_nodes}")

    for condition_node_id, condition_node_input_id in condition_nodes.items():
        if condition_node_id not in prompt.keys():
            continue

        try:
            # Filter conditions
            condition_node_class_type = prompt[condition_node_id]['class_type']
            conditions = dict()

            if condition_node_class_type == "FlowClipCondition":
                conditions = dict()
                gates_node_id, _ = prompt[condition_node_id]['inputs']['base']
                for gates_node_input_key, gates_node_input_value in prompt[gates_node_id]['inputs'].items():
                    if gates_node_input_key == "base":
                        trim_value = gates_node_input_value.strip()
                        if trim_value == "Pony":
                            conditions[0] = "SDXL"
                        elif len(trim_value) > 0:
                            conditions[0] = trim_value
            else:
                for node_input_id, node_input_value in prompt[condition_node_id]['inputs'].items():
                    if type(node_input_value) is bool:
                        conditions[node_input_id] = node_input_value
                    elif type(node_input_value) is str:
                        conditions[node_input_id] = node_input_value

            if len(conditions) == 0:
                raise ValueError

            prompt = remove_uncondition_nodes(prompt, condition_node_id, condition_node_input_id, conditions)

        except IOError:
            return (False,
            {
                'type': 'condition_io_mismatch',
                'message': 'Condition IO Type Mismatch',
                'details': 'input and output types do not match',
                'extra_info': {}
            }
            , [], [])

        except ValueError:
            return (False,
            {
                'type': 'condition_invalid_type',
                'message': 'Condition type is invalid',
                'details': 'conditions must be boolean or list',
                'extra_info': {}
            }
            , [], [])

    return original_validate(prompt_id, prompt, partial_execution_list)

