import { api } from '../../scripts/api.js';
import { getWidget } from "./node_tools.js";

function filterBase(node, filter) {
	const filterWidget = getWidget(node, 'filter');
	const loraNameWidget = getWidget(node, 'lora_name');

	if (filter === undefined)
		filter = filterWidget.value;

	filterWidget.value = filter;

	filter = filter.toLowerCase();

	api
	.fetchApi("/get_loras", {method: "POST"})
	.then((response) => response.json())
	.then((lora_names) => {
		loraNameWidget.options.length = 0;
		loraNameWidget.options.values = filter === 'all'
			? lora_names
			: lora_names.filter(name => name.startsWith(filter));

		if (loraNameWidget.options.include(loraNameWidget.value) === false)
			loraNameWidget.value = loraNameWidget.options.values.length > 0 ? loraNameWidget.options.values[0] : '';
	});
}

function loadInfo(node, loraName) {
	const loraNameWidget = getWidget(node, 'lora_name');
	const baseWidget = getWidget(node, 'base');
	const hashWidget = getWidget(node, 'hash');
	const triggersWidget = getWidget(node, 'triggers');
	const urlWidget = getWidget(node, 'url');

	if (loraName === undefined)
		loraName = loraNameWidget.value;

	loraNameWidget.value = loraName;

	const body = JSON.stringify({
		loraName: loraName
	});

	api
	  .fetchApi("/load_lora_info", {
			method: "POST",
			body: body,
			headers: {
				"content-type": "application/json",
			}
		})
	  .then((response) => response.json())
	  .then((resp) => {
		baseWidget.value = resp.base;
		hashWidget.value = resp.hash;
		triggersWidget.value = resp.triggers;
		urlWidget.value = resp.url;
	  });
}

function setBackgroundColor(node) {
	const bypassWidget = getWidget(node, 'bypass');
	if (bypassWidget.value == "Yes") {
		node.color = "#202020"
		node.bgcolor = "#252525"
		node.boxcolor = "#101010"
	} else {
		node.color = "#5a7a2c"
		node.bgcolor = "#45611d"
		node.boxcolor = "#26360e"
	}
}

function init(node, filter, loraName) {
	const bypassWidget = getWidget(node, 'bypass');
	const filterWidget = getWidget(node, 'filter');
	const loraNameWidget = getWidget(node, 'lora_name');

	bypassWidget.callback = () => {
		setBackgroundColor(node);
	};

	filterWidget.callback = () => {
		filterBase(node);
	};

	loraNameWidget.callback = () => {
		loadInfo(node);
	};

	filterBase(node, filter);
	loadInfo(node, loraName);
	setBackgroundColor(node);
}

export function nodeLoraLoaderCreated(node) {
	const loraNameWidget = getWidget(node, 'lora_name');
	const baseWidget = getWidget(node, 'base');
	const triggersWidget = getWidget(node, 'triggers');
	const urlWidget = getWidget(node, 'url');

	const openUrlWidget = node.addWidget("button", "Open URL", null, () => {
		const url = urlWidget.value;
		if (url !== undefined || url.length > 0)
			window.open(urlWidget.value);
	});

	const saveInfoWidget = node.addWidget("button", "Save Info", null, () => {
		const body = JSON.stringify({
			loraName: loraNameWidget.value,
			base: baseWidget.value,
			triggers: triggersWidget.value,
			url: urlWidget.value
		});

		api
		  .fetchApi("/save_lora_info", {
				method: "POST",
				body: body,
				headers: {
					"content-type": "application/json",
				}
			})
		  .then((response) => response.json())
		  .then((resp) => {
		  });
	});

	init(node);
}

export function nodeLoraLoaderLoaded(node) {
	if (node.widgets_values !== undefined) {
		const filter = node.widgets_values[1];
		const loraName = node.widgets_values[2];
		init(node, filter, loraName);
	} else {
		init(node);
	}
}
