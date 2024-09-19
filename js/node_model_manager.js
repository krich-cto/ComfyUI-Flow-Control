import { api } from '../../scripts/api.js';
import { getWidget } from "./node_tools.js";

export function nodeModelManagerCreated(node) {
	const typeWidget = getWidget(node, 'type');
	const fetchModelWidget = getWidget(node, 'fetch_model');

	const modelMoveWidget = node.addWidget("button", "Auto Arrange", null, () => {
		const body = JSON.stringify({
			type: typeWidget.value,
			fetchModel: fetchModelWidget.value
		});

		api
		  .fetchApi("/model_auto_arrange", {
				method: "POST",
				body: body,
				headers: {
					"content-type": "application/json",
				}
			});
	});
}

export function nodeModelManagerLoaded(node) {
}
