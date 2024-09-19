import { app } from "../../scripts/app.js";

function countWidgets(node, types) {
	let count = 0;
	for (let index = node.widgets.length - 1; index >= 0; index--) {
		const widget = node.widgets[index];
		if (types.includes(widget.type) === true) {
			count++;
		}
	}

	return count;
}

function removeWidgets(node, types) {
	for (let index = node.widgets.length - 1; index >= 0; index--) {
		const widget = node.widgets[index];
		if (types.includes(widget.type) === true) {
			node.widgets.splice(index, 1);
		}
	}
}

function removeExtraWidgets(node, types, max) {
	const count = countWidgets(node, types);
	let deleteCount = count > max ? count - max : 0;

	if (deleteCount > 0) {
		for (let index = node.widgets.length - 1; index >= 0; index--) {
			const widget = node.widgets[index];
			if (types.includes(widget.type) === true) {
				if (deleteCount <= 0)
					break;
	
				node.widgets.splice(index, 1);
				deleteCount--;
			}
		}
	}

	return count > max ? max : count;
}

function getWidgetDefaultValue(targetNode, index, values) {
	if (targetNode.widgets_values && index < targetNode.widgets_values.length) {
		const defaultValue = targetNode.widgets_values[index];
		if (values.includes(defaultValue))
			return defaultValue;
	}

	return values[0];
}

function init(node) {
	// Skip first index & count empty gate.
	let emptyGateCount = 0;
	for (let index = 1; index < node.widgets.length; index++) {
		const widget = node.widgets[index];
		if (widget.value.trim().length === 0) {
			emptyGateCount++;
		}
	}

	if (emptyGateCount == 0) {
		addGate(node, node.widgets.length);
	} else if (emptyGateCount > 1) {
		// Delete all empty gates.
		for (let index = node.widgets.length - 1; index > 0; index--) {
			const widget = node.widgets[index];
			if (widget.value.trim().length == 0) {
				node.widgets.splice(index, 1);
			}
		}

		// Rename gates.
		for (let index = 1; index < node.widgets.length; index++) {
			const widget = node.widgets[index];
			widget.name = `gate_${index}`;
		}

		// Add new empty gate at bottom.
		addGate(node, node.widgets.length);
	}

	if (node.outputs[0].links) {
		node.outputs[0].links.forEach(link_id => {
			const linkInfo = app.graph.links[link_id];
			const targetNode = app.graph._nodes_by_id[linkInfo.target_id];
			nodeGateApply(node, targetNode);
		});
	}
}

export function nodeGateApply(node, targetNode) {
	const gateWidgets = [];
	const output = node.widgets[0].value;

	// Skip first index & empty gate
	for (let index = 1; index < node.widgets.length; index++) {
		const widget = node.widgets[index];
		if (widget.value.trim().length > 0)
			gateWidgets.push(widget);
	}

	const gateValues = gateWidgets.map(w => w.value); // Not include output type
	const gateCount = gateWidgets.length; // Not include output type

	if (gateCount <= 1) {
		removeWidgets(targetNode, ['combo', 'toggle'])
	} else if (output == 'Multiple') {
		removeWidgets(targetNode, ['combo'])
		const remainCount = removeExtraWidgets(targetNode, ['toggle'], gateCount);
		let widgetIndex = targetNode.widgets.length;
		let addCount = gateCount - remainCount;
		while (addCount > 0) {
			targetNode.addWidget('toggle', `temp_${addCount}`, false, () => { }, { on: 'ON', off: 'OFF' });
			addCount--;
			widgetIndex++;
		}
				
		let gateIndex = 0;
		for (let index = 0; index < targetNode.widgets.length; index++) {
			const widget = targetNode.widgets[index];
			if (widget.type == 'toggle') {
				const defaultValue = getWidgetDefaultValue(targetNode, index, [true, false]);
				widget.name = gateWidgets[gateIndex++].value;
				widget.value = defaultValue;
				widget.options = { on: 'ON', off: 'OFF' };
			}
		}
	// Toggle is not make sense. So remove it.
	// } else if (gateCount == 2) {
	// 	removeWidgets(targetNode, ['combo'])
	// 	const remainCount = removeExtraWidgets(targetNode, ['toggle'], 1);
	// 	if (remainCount <= 0)
	// 		targetNode.addWidget('toggle', 'condition', true, () => { }, { on: gateValues[0], off: gateValues[1] });
	// 	else {
	// 		for (let index = 0; index < targetNode.widgets.length; index++) {
	// 			const widget = targetNode.widgets[index];
	// 			if (widget.type == 'toggle') {
	// 				widget.name = 'condition';
	// 				widget.options = { on: gateValues[0], off: gateValues[1] };
	// 			}
	// 		}
	// 	}
	} else if (gateCount >= 2) {
		removeWidgets(targetNode, ['toggle'])
		const remainCount = removeExtraWidgets(targetNode, ['combo'], 1);
		if (remainCount <= 0) {
			const defaultValue = getWidgetDefaultValue(targetNode, targetNode.widgets.length, gateValues);
			targetNode.addWidget('combo', 'select', defaultValue, () => { }, { values: gateValues });
		} else {
			for (let index = 0; index < targetNode.widgets.length; index++) {
				const widget = targetNode.widgets[index];
				if (widget.type == 'combo') {
					const defaultValue = getWidgetDefaultValue(targetNode, index, gateValues);
					widget.name = gateWidgets[0].value;
					widget.options = { values: gateValues };
				}
			}
		}
	}

	// Remove target extra outputs
	if (targetNode.outputs.length > gateCount) {
		targetNode.outputs.splice(gateCount, targetNode.outputs.length - gateCount);
	}

	// Add/Edit target outputs
	let target_output_index = 0;
	gateWidgets.forEach(widget => {
		if (target_output_index < targetNode.outputs.length) {
			targetNode.outputs[target_output_index].name = widget.value;
			targetNode.outputs[target_output_index].type = targetNode.inputs[0].type;
		} else {
			targetNode.addOutput(widget.value, targetNode.inputs[0].type);
		}

		target_output_index++;
	});
}

function addGate(node, no, value = '') {
	if (no > 9)
		return;

	const widget = node.addWidget('text', `gate_${no}`, value, () => { }, {})
	widget.callback = () => {
		init(node);
	};
}

export function nodeGateCreated(node) {
	node.widgets.forEach(widget => {
		widget.callback = () => {
			init(node)
		};
	});

	init(node);
}

export function nodeGateLoaded(node) {
	// Assign call back to output type.
	node.widgets[0].callback = () => {
		init(node);
	};

	// Add gates until equal with values.
	for (let index = node.widgets.length; index < node.widgets_values.length; index++) {
		addGate(node, index, node.widgets_values[index]);
	}

	init(node);
}

