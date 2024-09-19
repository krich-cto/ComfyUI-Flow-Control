import { ComfyApp, app } from "../../scripts/app.js";
import { ComfyDialog, $el } from "../../scripts/ui.js";
import { api } from "../../scripts/api.js";
import { nodeCkptPresetLoaderCreated, nodeCkptPresetLoaderLoaded } from "./node_checkpoint_preset_loader.js";
import { nodeFluxPresetLoaderCreated, nodeFluxPresetLoaderLoaded } from "./node_flux_preset_loader.js";
import { nodeLoraLoaderCreated, nodeLoraLoaderLoaded } from "./node_lora_loader.js";
import { nodeGateCreated, nodeGateLoaded, nodeGateApply } from "./node_gate.js";
import { nodeModelManagerCreated, nodeModelManagerLoaded } from "./node_model_manager.js";

app.registerExtension({
	name: "Comfy.Flow.Control",

	async nodeCreated(node, app) {
		if (node.comfyClass == 'FlowCheckpointPresetLoader') {
			nodeCkptPresetLoaderCreated(node);
		} else if (node.comfyClass == 'FlowFluxPresetLoader') {
			nodeFluxPresetLoaderCreated(node);
		} else if (node.comfyClass == 'FlowLoraLoader' || node.comfyClass == 'FlowLoraLoaderModelOnly') {
			nodeLoraLoaderCreated(node);
		} else if (node.comfyClass == 'FlowGate') {
			nodeGateCreated(node);
		} else if (node.comfyClass == 'FlowModelManager') {
			nodeModelManagerCreated(node);
		}
	},
	async loadedGraphNode(node, app) {
		if (node.type == 'FlowCheckpointPresetLoader') {
			nodeCkptPresetLoaderLoaded(node);
		} else if (node.type == 'FlowFluxPresetLoader') {
			nodeFluxPresetLoaderLoaded(node);
		} else if (node.comfyClass == 'FlowLoraLoader' || node.comfyClass == 'FlowLoraLoaderModelOnly') {
			nodeLoraLoaderLoaded(node);
		} else if (node.type == 'FlowGate') {
			nodeGateLoaded(node);
		} else if (node.type == 'FlowModelManager') {
			nodeModelManagerLoaded(node);
		}
	},
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === 'FlowGate') {
			const onConnectionsChange = nodeType.prototype.onConnectionsChange;
			nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
				if (!link_info)
					return;

				if (type == LiteGraph.OUTPUT) {
					if (connected && index == 0) {
						const target_node = app.graph._nodes_by_id[link_info.target_id];
						nodeGateApply(this, target_node);
					}

					return;
				}
			}
		}

		const autoInputNodes = [
			{ id: 'FlowConditioningAutoSwitch', inputId: 'conditioning' },
			{ id: 'FlowImageAutoBatch', inputId: 'image' },
			{ id: 'FlowLatentAutoBatch', inputId: 'latent' },
		];
		if (autoInputNodes.map(n => n.id).includes(nodeData.name)) {
			const autoInputNode = autoInputNodes.find(n => n.id === nodeData.name);

			const onConnectionsChange = nodeType.prototype.onConnectionsChange;
			nodeType.prototype.onConnectionsChange = function (type, index, connected, link_info) {
				if (!link_info)
					return;

				// If not connected, node should have only 1 input left.
				if (!connected && (this.inputs.length > 1)) {
					const stackTrace = new Error().stack;

					if (!stackTrace.includes('LGraphNode.prototype.connect') && // for touch device
						!stackTrace.includes('LGraphNode.connect') && // for mouse device
						!stackTrace.includes('loadGraphData'))
						this.removeInput(index);
				}

				// Rename old inputs.
				let input_no = 1;
				for (let index = 0; index < this.inputs.length; index++) {
					const input = this.inputs[index];
					input.name = `${autoInputNode.inputId}_${input_no}`
					input_no++;
				}

				// Add the new one.
				let lastInput = this.inputs[this.inputs.length - 1];
				if (lastInput.link != undefined) {
					this.addInput(`${autoInputNode.inputId}_${input_no}`, this.outputs[0].type);
				}
			}
		}
	}
});
