import { api } from '../../scripts/api.js';
import { getWidget } from "./node_tools.js";

function filterBase(node, filter) {
	const filterWidget = getWidget(node, 'filter');
	const ckptNameWidget = getWidget(node, 'ckpt_name');

	if (filter === undefined)
		filter = filterWidget.value;

	filterWidget.value = filter;

	filter = filter.toLowerCase();

	api
	.fetchApi("/get_ckpts", {method: "POST"})
	.then((response) => response.json())
	.then((checkpoint_names) => {
		ckptNameWidget.options.length = 0;
		ckptNameWidget.options.values = filter === 'all'
			? checkpoint_names
			: checkpoint_names.filter(name => name.startsWith(filter));

		if (ckptNameWidget.options.include(ckptNameWidget.value) === false)
			ckptNameWidget.value = ckptNameWidget.options.values.length > 0 ? ckptNameWidget.options.values[0] : '';
	});
}

function loadPreset(node, ckptName) {
	const ckptNameWidget = getWidget(node, 'ckpt_name');
	const vaeNameWidget = getWidget(node, 'vae_name');
	const baseWidget = getWidget(node, 'base');
	const hashWidget = getWidget(node, 'hash');
	const stepsWidget = getWidget(node, 'steps');
	const cfgWidget = getWidget(node, 'cfg');
	const clipSkipWidget = getWidget(node, 'clip_skip');
	const samplerNameWidget = getWidget(node, 'sampler_name');
	const schedulerWidget = getWidget(node, 'scheduler');
	const urlWidget = getWidget(node, 'url');

	if (ckptName === undefined)
		ckptName = ckptNameWidget.value;

	ckptNameWidget.value = ckptName;

	const body = JSON.stringify({
		ckptName: ckptName
	});

	api
	  .fetchApi("/load_ckpt_preset", {
			method: "POST",
			body: body,
			headers: {
				"content-type": "application/json",
			}
		})
	  .then((response) => response.json())
	  .then((resp) => {
		vaeNameWidget.value = resp.vaeName;
		baseWidget.value = resp.base;
		hashWidget.value = resp.hash;
		stepsWidget.value = resp.steps;
		cfgWidget.value = resp.cfg;
		clipSkipWidget.value = resp.clipSkip;
		samplerNameWidget.value = resp.samplerName;
		schedulerWidget.value = resp.scheduler;
		urlWidget.value = resp.url;
	  });
}

function init(node, filter, ckptName) {
	const filterWidget = getWidget(node, 'filter');
	const ckptNameWidget = getWidget(node, 'ckpt_name');
	filterWidget.callback = () => {
		filterBase(node);
	};

	ckptNameWidget.callback = () => {
		loadPreset(node);
	};

	filterBase(node, filter);
	loadPreset(node, ckptName);
}

export function nodeCkptPresetLoaderCreated(node) {
	console.log('nodeCkptPresetLoaderCreated');

	const ckptNameWidget = getWidget(node, 'ckpt_name');
	const vaeNameWidget = getWidget(node, 'vae_name');
	const baseWidget = getWidget(node, 'base');
	const stepsWidget = getWidget(node, 'steps');
	const cfgWidget = getWidget(node, 'cfg');
	const clipSkipWidget = getWidget(node, 'clip_skip');
	const samplerNameWidget = getWidget(node, 'sampler_name');
	const schedulerWidget = getWidget(node, 'scheduler');
	const urlWidget = getWidget(node, 'url');

	// const loadPresetWidget = node.addWidget("button", "Load Preset", null, () => {
	// 	const body = JSON.stringify({
	// 		ckptName: ckptNameWidget.value
	// 	});

	// 	api
	// 	  .fetchApi("/load_ckpt_preset", {
	// 			method: "POST",
	// 			body: body,
	// 			headers: {
	// 				"content-type": "application/json",
	// 			}
	// 		})
	// 	  .then((response) => response.json())
	// 	  .then((resp) => {
	// 		vaeNameWidget.value = resp.vaeName;
	// 		baseWidget.value = resp.base;
	// 		hashWidget.value = resp.hash;
	// 		stepsWidget.value = resp.steps;
	// 		cfgWidget.value = resp.cfg;
	// 		clipSkipWidget.value = resp.clipSkip;
	// 		samplerNameWidget.value = resp.samplerName;
	// 		schedulerWidget.value = resp.scheduler;
	// 	  });
	// });

	const openUrlWidget = node.addWidget("button", "Open URL", null, () => {
		const url = urlWidget.value;
		if (url !== undefined || url.length > 0)
			window.open(urlWidget.value);
	});

	const savePresetWidget = node.addWidget("button", "Save Preset", null, () => {
		const body = JSON.stringify({
			ckptName: ckptNameWidget.value,
			vaeName: vaeNameWidget.value,
			base: baseWidget.value,
			steps: stepsWidget.value,
			cfg: cfgWidget.value,
			clipSkip: clipSkipWidget.value,
			samplerName: samplerNameWidget.value,
			scheduler: schedulerWidget.value,
			url: urlWidget.value
		});

		api
		  .fetchApi("/save_ckpt_preset", {
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

export function nodeCkptPresetLoaderLoaded(node) {
	console.log('nodeCkptPresetLoaderLoaded');

	if (node.widgets_values !== undefined) {
		const filter = node.widgets_values[0];
		const ckptName = node.widgets_values[1];
		init(node, filter, ckptName);
	} else {
		init(node);
	}
}
