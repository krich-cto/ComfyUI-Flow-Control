import { api } from '../../scripts/api.js';
import { getWidget } from "./node_tools.js";

function loadPreset(node, unetName) {
	const unetNameWidget = getWidget(node, 'unet_name');
	const vaeNameWidget = getWidget(node, 'vae_name');
	const clipName1Widget = getWidget(node, 'clip_name1');
	const clipName2Widget = getWidget(node, 'clip_name2');
	const baseWidget = getWidget(node, 'base');
	const hashWidget = getWidget(node, 'hash');
	const stepsWidget = getWidget(node, 'steps');
	const guidanceWidget = getWidget(node, 'guidance');
	const samplerNameWidget = getWidget(node, 'sampler_name');
	const schedulerWidget = getWidget(node, 'scheduler');
	const urlWidget = getWidget(node, 'url');

	if (unetName === undefined)
		unetName = unetNameWidget.value;

	unetNameWidget.value = unetName;

	const body = JSON.stringify({
		unetName: unetName
	});

	api
	  .fetchApi("/load_flux_preset", {
			method: "POST",
			body: body,
			headers: {
				"content-type": "application/json",
			}
		})
	  .then((response) => response.json())
	  .then((resp) => {
		vaeNameWidget.value = resp.vaeName;
		clipName1Widget.value = resp.clipName1;
		clipName2Widget.value = resp.clipName2;
		baseWidget.value = resp.base;
		hashWidget.value = resp.hash;
		stepsWidget.value = resp.steps;
		guidanceWidget.value = resp.guidance;
		samplerNameWidget.value = resp.samplerName;
		schedulerWidget.value = resp.scheduler;
		urlWidget.value = resp.url;
	  });
}

function init(node, unetName) {
	const unetNameWidget = getWidget(node, 'unet_name');

	unetNameWidget.callback = () => {
		loadPreset(node);
	};

	loadPreset(node, unetName);
}

export function nodeFluxPresetLoaderCreated(node) {
	const unetNameWidget = getWidget(node, 'unet_name');
	const vaeNameWidget = getWidget(node, 'vae_name');
	const clipName1Widget = getWidget(node, 'clip_name1');
	const clipName2Widget = getWidget(node, 'clip_name2');
	const baseWidget = getWidget(node, 'base');
	const stepsWidget = getWidget(node, 'steps');
	const guidanceWidget = getWidget(node, 'guidance');
	const samplerNameWidget = getWidget(node, 'sampler_name');
	const schedulerWidget = getWidget(node, 'scheduler');
	const urlWidget = getWidget(node, 'url');

	const openUrlWidget = node.addWidget("button", "Open URL", null, () => {
		const url = urlWidget.value;
		if (url !== undefined || url.length > 0)
			window.open(urlWidget.value);
	});

	const savePresetWidget = node.addWidget("button", "Save Preset", null, () => {
		const body = JSON.stringify({
			unetName: unetNameWidget.value,
			vaeName: vaeNameWidget.value,
			clipName1: clipName1Widget.value,
			clipName2: clipName2Widget.value,
			base: baseWidget.value,
			steps: stepsWidget.value,
			guidance: guidanceWidget.value,
			samplerName: samplerNameWidget.value,
			scheduler: schedulerWidget.value,
			url: urlWidget.value
		});

		api
		  .fetchApi("/save_flux_preset", {
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

export function nodeFluxPresetLoaderLoaded(node) {
	if (node.widgets_values !== undefined) {
		const unetName = node.widgets_values[0];
		init(node, unetName);
	} else {
		init(node);
	}
}
