export function getWidget(node, widgetName) {
	for (let index = 0; index < node.widgets.length; index++) {
		const widget = node.widgets[index];
		if (widget.name == widgetName) {
			return widget;
		}
	}

	return undefined;
}