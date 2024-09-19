import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyDialog, $el } from "../../scripts/ui.js";
import { ComfyApp } from "../../scripts/app.js";
import { ClipspaceDialog } from "../../extensions/core/clipspace.js";

// Helper function to convert a data URL to a Blob object
function dataURLToBlob(dataURL) {
	const parts = dataURL.split(";base64,");
	const contentType = parts[0].split(":")[1];
	const byteString = atob(parts[1]);
	const arrayBuffer = new ArrayBuffer(byteString.length);
	const uint8Array = new Uint8Array(arrayBuffer);
	for (let i = 0; i < byteString.length; i++) {
		uint8Array[i] = byteString.charCodeAt(i);
	}
	return new Blob([arrayBuffer], { type: contentType });
}

function loadImage(imagePath) {
	return new Promise((resolve, reject) => {
		const image = new Image();
		image.onload = function () {
			resolve(image);
		};
		image.src = imagePath;
	});
}

function loadedImageToBlob(image) {
	const canvas = document.createElement('canvas');

	canvas.width = image.width;
	canvas.height = image.height;

	const ctx = canvas.getContext('2d');

	ctx.drawImage(image, 0, 0);

	const dataURL = canvas.toDataURL('image/png', 1);
	const blob = dataURLToBlob(dataURL);

	return blob;
}

function prepare_mask(image, maskCanvas, maskContext, maskColor) {
	maskContext.drawImage(image, 0, 0, maskCanvas.width, maskCanvas.height);
	const maskData = maskContext.getImageData(
		0,
		0,
		maskCanvas.width,
		maskCanvas.height
	);
	for (let i = 0; i < maskData.data.length; i += 4) {
		if (maskData.data[i + 3] == 255) maskData.data[i + 3] = 0;
		else maskData.data[i + 3] = 255;
		maskData.data[i] = maskColor.r;
		maskData.data[i + 1] = maskColor.g;
		maskData.data[i + 2] = maskColor.b;
	}
	maskContext.globalCompositeOperation = "source-over";
	maskContext.putImageData(maskData, 0, 0);
}

async function uploadMask(filepath, formData) {
	await api.fetchApi("/upload/mask", {
		method: "POST",
		body: formData
	}).then((response) => {
	}).catch((error) => {
		console.error("Error:", error);
	});
	ComfyApp.clipspace.imgs[ComfyApp.clipspace["selectedIndex"]] = new Image();
	ComfyApp.clipspace.imgs[ComfyApp.clipspace["selectedIndex"]].src = api.apiURL(
		"/view?" + new URLSearchParams(filepath).toString() + app.getPreviewFormatParam() + app.getRandParam()
	);
	if (ComfyApp.clipspace.images)
		ComfyApp.clipspace.images[ComfyApp.clipspace["selectedIndex"]] = filepath;
	ClipspaceDialog.invalidatePreview();
}

class MaskEditorExDialog extends ComfyDialog {
	static instance = null;
	static mousedown_x = null;
	static mousedown_y = null;
	brush;
	brush_size_slider;
	brush_opacity_slider;
	colorButton;
	saveButton;
	imgCanvas;
	last_display_style;
	is_visible;
	handler_registered;
	brush_slider_input;
	last_pressure;

	image;
	imageMaskCanvas;
	outputCanvas;
	outputContext;
	outputCanvasRect;
	imageCanvas;
	imageContext;
	imageCanvasRect;
	maskCanvas;
	maskContext;
	cursorPoint;
	pointerCaptureId;
	pointerDownPoint;
	imageResizeTL;
	imageResizeTR;
	imageResizeBL;
	imageResizeBR;
	minX;
	minY;
	maxX;
	maxY;
	maxBrushFontSize = 30;
	outputMargin = 40;
	outputResizeGripDistance = 20;
	outputResizeGripShortSize = 8;
	outputResizeGripLongSize = 40;
	imageResizeGripSize = 14;
	imageRatio;
	zoomRatio;
	imageOffsetPoint = { x: 0, y: 0 };
	imageRect;				// Image rectangle in actual scale.
	outputRect;				// Output rectangle in actual scale.
	outputWidthCtrl;
	outputHeightCtrl;

	static instance = null;

	static getInstance() {
		if (!MaskEditorExDialog.instance) {
			MaskEditorExDialog.instance = new MaskEditorExDialog();
		}
		return MaskEditorExDialog.instance;
	}
	is_layout_created = false;
	constructor() {
		super();
		this.element = $el("div.comfy-modal", { parent: document.body, style: { padding: "20px" } }, [
			$el("div.comfy-modal-content", [...this.createButtons()])
		]);
	}
	createButtons() {
		return [];
	}
	createButton(name, callback) {
		var button = document.createElement("button");
		button.style.pointerEvents = "auto";
		button.innerText = name;
		button.addEventListener("click", callback);
		return button;
	}
	createLeftPanel() {
		const divElement = document.createElement("div");
		divElement.style.width = "150px";
		divElement.style.height = "100%";
		return divElement;
	}
	createAdjustmentButton(name, callback) {
		const divElement = document.createElement("div");
		divElement.style.boxSizing = "border-box";
		divElement.style.flexGrow = "1";
		divElement.style.width = "33.33%";
		divElement.style.height = "50px";
		divElement.style.overflow = "hidden";
		divElement.style.listStyle = "none";

		var button = this.createButton(name, callback);
		button.innerText = name;
		button.style.width = "100%";
		button.style.height = "100%";
		button.style.margin = "0px";
		
		divElement.appendChild(button);
		return divElement;
	}
	createAdjustmentPanel() {
		const divElement = document.createElement("div");
		divElement.style.marginTop = "10px";
		divElement.style.display = "flex";
		divElement.style.flexWrap = "wrap";
		divElement.style.width = "150px";

		const alignTopLeftButton = this.createAdjustmentButton('↖', (event) => {});
		const alignTopButton = this.createAdjustmentButton('↑', (event) => {});
		const alignTopRightButton = this.createAdjustmentButton('↗', (event) => {});
		const alignLeftButton = this.createAdjustmentButton('←', (event) => {});
		const resizeFitButton = this.createAdjustmentButton('⛶', (event) => {});
		const alignRightButton = this.createAdjustmentButton('→', (event) => {});
		const alignBottomLeftButton = this.createAdjustmentButton('↙', (event) => {});
		const alignBottomButton = this.createAdjustmentButton('↓', (event) => {});
		const alignBottomRightButton = this.createAdjustmentButton('↘', (event) => {});
		
		divElement.appendChild(alignTopLeftButton);
		divElement.appendChild(alignTopButton);
		divElement.appendChild(alignTopRightButton);
		divElement.appendChild(alignLeftButton);
		divElement.appendChild(resizeFitButton);
		divElement.appendChild(alignRightButton);
		divElement.appendChild(alignBottomLeftButton);
		divElement.appendChild(alignBottomButton);
		divElement.appendChild(alignBottomRightButton);
		
		return divElement;
	}
	createLeftPanelButton(name, valign, callback) {
		var button = this.createButton(name, callback);

		if (this.leftPanelBottom === undefined)
			this.leftPanelBottom = 20;

		if (valign == "bottom") {
			button.style.position = "absolute";
			button.style.left = "20px";
			button.style.bottom = `${this.leftPanelBottom}px`;
			button.style.width = "150px";

			this.leftPanelBottom += 30;
		} else {
			button.style.width = "100%";
		}

		return button;
	}
	createLeftPanelSlider(id, name, min, max, step, value, callback) {
		const divElement = document.createElement("div");
		divElement.id = id;
		divElement.style.fontFamily = "sans-serif";
		divElement.style.color = "var(--input-text)";
		divElement.style.backgroundColor = "var(--comfy-input-bg)";
		divElement.style.borderRadius = "8px";
		divElement.style.borderColor = "var(--border-color)";
		divElement.style.borderStyle = "solid";
		divElement.style.fontSize = "15px";
		divElement.style.padding = "1px 6px";
		divElement.style.position = "relative";
		divElement.style.top = "2px";
		divElement.style.width = "100%";
		divElement.style.pointerEvents = "auto";
		const inputElement = document.createElement("input");
		inputElement.setAttribute("type", "range");
		inputElement.setAttribute("min", min);
		inputElement.setAttribute("max", max);
		inputElement.setAttribute("step", step);
		inputElement.setAttribute("value", value);
		const labelElement = document.createElement("label");
		labelElement.textContent = name;
		divElement.appendChild(labelElement);
		divElement.appendChild(inputElement);
		inputElement.addEventListener("change", callback);
		return [divElement, inputElement];
	}
	createLeftPanelNumber(id, name, value, callback) {
		const divElement = document.createElement("div");
		divElement.id = id;
		divElement.style.fontFamily = "sans-serif";
		divElement.style.color = "var(--input-text)";
		divElement.style.backgroundColor = "var(--comfy-input-bg)";
		divElement.style.borderRadius = "8px";
		divElement.style.borderColor = "var(--border-color)";
		divElement.style.borderStyle = "solid";
		divElement.style.fontSize = "15px";
		divElement.style.padding = "1px 6px";
		divElement.style.position = "relative";
		divElement.style.top = "2px";
		divElement.style.width = "100%";
		divElement.style.pointerEvents = "auto";
		const inputElement = document.createElement("input");
		inputElement.setAttribute("type", "number");
		inputElement.setAttribute("value", value);
		inputElement.style.width = "100%";
		const labelElement = document.createElement("label");
		labelElement.textContent = name;
		divElement.appendChild(labelElement);
		divElement.appendChild(inputElement);
		inputElement.addEventListener("change", callback);
		return [divElement, inputElement];
	}
	createOutputResizeGrip(id, cursor) {
		const self = this;
		const divElement = document.createElement("div");
		divElement.id = id;
		divElement.style.position = "absolute";
		divElement.style.background = "#FFFFFF80";
		divElement.style.border = "1px #000 solid";
		divElement.style.borderRadius = "4px";
		divElement.style.visibility = "hidden";
		if (cursor == "ew-resize") {
			divElement.style.width = `${this.outputResizeGripShortSize}px`;
			divElement.style.height = `${this.outputResizeGripLongSize}px`;
		} else {
			divElement.style.width = `${this.outputResizeGripLongSize}px`;
			divElement.style.height = `${this.outputResizeGripShortSize}px`;
		}

		divElement.style.cursor = cursor;
		divElement.addEventListener(
			"pointerdown",
			(event) => { 
				self.pointerCaptureId = id;
				self.pointerDownPoint = { x: event.pageX, y: event.pageY };
			}
		);

		return divElement;
	}
	createImageResizeGrip(id, cursor) {
		const self = this;
		const divElement = document.createElement("div");
		divElement.id = id;
		divElement.style.position = "absolute";
		divElement.style.background = "white";
		divElement.style.border = "1px #000 solid";
		divElement.style.borderRadius = "4px";
		divElement.style.visibility = "hidden";
		divElement.style.width = `${this.imageResizeGripSize}px`;
		divElement.style.height = `${this.imageResizeGripSize}px`;
		divElement.style.cursor = cursor;
		divElement.addEventListener(
			"pointerdown",
			(event) => { 
				self.pointerCaptureId = id;
				self.pointerDownPoint = { x: event.pageX, y: event.pageY };
			}
		);

		return divElement;
	}
	setlayout() {
		const self = this;
		var leftPanel = this.createLeftPanel();
		var brush = document.createElement("div");
		let ctrl, input;
		brush.id = "brush";
		brush.style.backgroundColor = "transparent";
		brush.style.outline = "1px dashed black";
		brush.style.boxShadow = "0 0 0 1px white";
		brush.style.borderRadius = "50%";
		brush.style.MozBorderRadius = "50%";
		brush.style.WebkitBorderRadius = "50%";
		brush.style.position = "absolute";
		brush.style.zIndex = "8889";
		brush.style.pointerEvents = "none";
		brush.style.textAlign = "center";
		brush.style.verticalAlign = "middle";
		brush.style.lineHeight = "middle";
		brush.style.color = "black";
		brush.style.fontSize = "15px";
		brush.textContent = "+";
		this.brush = brush;
		this.element.appendChild(this.outputCanvas);
		this.element.appendChild(this.imageCanvas);
		this.element.appendChild(this.maskCanvas);

		this.outputResizeL = this.createOutputResizeGrip("outputResizeL", "ew-resize");
		this.outputResizeR = this.createOutputResizeGrip("outputResizeR", "ew-resize");
		this.outputResizeT = this.createOutputResizeGrip("outputResizeT", "ns-resize");
		this.outputResizeB = this.createOutputResizeGrip("outputResizeB", "ns-resize");
		this.imageResizeTL = this.createImageResizeGrip("imageResizeTL", "nwse-resize");
		this.imageResizeTR = this.createImageResizeGrip("imageResizeTR", "nesw-resize");
		this.imageResizeBL = this.createImageResizeGrip("imageResizeBL", "nesw-resize");
		this.imageResizeBR = this.createImageResizeGrip("imageResizeBR", "nwse-resize");
		this.element.appendChild(this.outputResizeL);
		this.element.appendChild(this.outputResizeR);
		this.element.appendChild(this.outputResizeT);
		this.element.appendChild(this.outputResizeB);
		this.element.appendChild(this.imageResizeTL);
		this.element.appendChild(this.imageResizeTR);
		this.element.appendChild(this.imageResizeBL);
		this.element.appendChild(this.imageResizeBR);

		this.element.appendChild(leftPanel);
		document.body.appendChild(brush);
		var clearButton = this.createLeftPanelButton("Clear", "top", () => {
			self.maskContext.clearRect(
				0,
				0,
				self.maskCanvas.width,
				self.maskCanvas.height
			);
		});
		this.colorButton = this.createLeftPanelButton(this.getColorButtonText(), "top", () => {
			if (self.brush_color_mode === "black") {
				self.brush_color_mode = "white";
			} else if (self.brush_color_mode === "white") {
				self.brush_color_mode = "negative";
			} else {
				self.brush_color_mode = "black";
			}
			self.updateWhenBrushColorModeChanged();
		});

		[ctrl, input] = this.createLeftPanelSlider(
			"maskeditor-thickness-slider",
			"Thickness",
			1,
			100,
			1,
			10,
			(event) => {
				self.brush_size = event.target.value;
				self.updateBrushPreview(self);
			}
		);

		this.brush_size_slider = ctrl;
		this.brush_slider_input = input;

		[ctrl, input] = this.createLeftPanelSlider(
			"maskeditor-opacity-slider",
			"Opacity",
			0.1,
			1,
			0.01,
			0.7,
			(event) => {
				self.brush_opacity = event.target.value;
				if (self.brush_color_mode !== "negative") {
					self.maskCanvas.style.opacity = self.brush_opacity.toString();
				}
			}
		);

		this.brush_opacity_slider = ctrl;
		this.opacity_slider_input = input;

		[ctrl, input] = this.createLeftPanelNumber(
			"maskeditor-output-width",
			"Output Width",
			0,
			(event) => {
				self.changeOutputWidth(self.outputWidthInput.value);
			}
		);

		this.outputWidthCtrl = ctrl;
		this.outputWidthInput = input;

		[ctrl, input] = this.createLeftPanelNumber(
			"maskeditor-output-height",
			"Output Height",
			0,
			(event) => {
				self.changeOutputHeight(self.outputHeightInput.value);
			}
		);

		this.outputHeightCtrl = ctrl;
		this.outputHeightInput = input;

		var adjustmentPanel = this.createAdjustmentPanel();

		var cancelButton = this.createLeftPanelButton("Cancel", "bottom", () => {
			document.removeEventListener("keydown", MaskEditorExDialog.handleKeyDown);
			self.close();
		});

		this.saveButton = this.createLeftPanelButton("Save", "bottom", () => {
			document.removeEventListener("keydown", MaskEditorExDialog.handleKeyDown);
			self.save();
		});

		leftPanel.appendChild(clearButton);
		leftPanel.appendChild(this.colorButton);
		leftPanel.appendChild(this.brush_size_slider);
		leftPanel.appendChild(this.brush_opacity_slider);
		leftPanel.appendChild(this.outputWidthCtrl);
		leftPanel.appendChild(this.outputHeightCtrl);
		leftPanel.appendChild(adjustmentPanel);
		leftPanel.appendChild(this.saveButton);
		leftPanel.appendChild(cancelButton);

		this.outputCanvas.style.position = "absolute";
		this.outputCanvas.style.top = "20px";
		this.outputCanvas.style.left = "190px";
		this.outputCanvas.style.border = "1px #FFF solid";
		this.outputCanvas.style.borderRadius = "4px";
		this.imageCanvas.style.position = "absolute";
		this.imageCanvas.style.top = "20px";
		this.imageCanvas.style.left = "190px";
		this.imageCanvas.style.border = "1px #FFF solid";
		this.imageCanvas.style.borderRadius = "4px";
		this.maskCanvas.style.position = "absolute";
		this.maskCanvas.style.top = "20px";
		this.maskCanvas.style.left = "190px";
		this.maskCanvas.style.cursor = "none";
		const maskCanvasStyle = this.getMaskCanvasStyle();
		this.maskCanvas.style.mixBlendMode = maskCanvasStyle.mixBlendMode;
		this.maskCanvas.style.opacity = maskCanvasStyle.opacity.toString();
	}
	async show() {
		this.zoom_ratio = 1;
		this.pan_x = 0;
		this.pan_y = 0;
		if (!this.is_layout_created) {
			const outputCanvas = document.createElement("canvas");
			const imageCanvas = document.createElement("canvas");
			const maskCanvas = document.createElement("canvas");
			outputCanvas.id = "outputCanvas";
			imageCanvas.id = "imageCanvas";
			maskCanvas.id = "maskCanvas";
			this.outputCanvas = outputCanvas;
			this.imageCanvas = imageCanvas;
			this.maskCanvas = maskCanvas;
			this.outputContext = outputCanvas.getContext("2d", { willReadFrequently: true });
			this.imageContext = imageCanvas.getContext("2d", { willReadFrequently: true });
			this.maskContext = maskCanvas.getContext("2d", { willReadFrequently: true });
			
			this.setlayout();
			this.setEventHandler(maskCanvas);
			this.is_layout_created = true;
			const self = this;
			const observer = new MutationObserver(function (mutations) {
				mutations.forEach(function (mutation) {
					if (mutation.type === "attributes" && mutation.attributeName === "style") {
						if (self.last_display_style && self.last_display_style != "none" && self.element.style.display == "none") {
							self.brush.style.display = "none";
							ComfyApp.onClipspaceEditorClosed();
						}
						self.last_display_style = self.element.style.display;
					}
				});
			});
			const config = { attributes: true };
			observer.observe(this.element, config);
		}
		document.addEventListener("keydown", MaskEditorExDialog.handleKeyDown);
		if (ComfyApp.clipspace_return_node) {
			this.saveButton.innerText = "Save to node";
		} else {
			this.saveButton.innerText = "Save";
		}
		this.saveButton.disabled = false;
		this.element.style.display = "block";
		this.element.style.width = "85%";
		this.element.style.margin = "0 7.5%";
		this.element.style.height = "100vh";
		this.element.style.top = "50%";
		this.element.style.left = "42%";
		this.element.style.zIndex = "8888";
		await this.setImages();
		this.is_visible = true;
	}
	isOpened() {
		return this.element.style.display == "block";
	}
	printRect(name, rect) {
		console.log(`${name} [${rect.width / rect.height}] - ${rect.x},${rect.y} (${rect.width}x${rect.height})`);
	}
	copyRect(rect) {
		return {
			x: rect.x,
			y: rect.y,
			width: rect.width,
			height: rect.height
		};
	}
	setElementRect(element, rect) {
		element.style.left = `${rect.x}px`;
		element.style.top = `${rect.y}px`;
		element.style.width = `${rect.width}px`;
		element.style.height = `${rect.height}px`;

		element.width = rect.width;
		element.height = rect.height;
	}
	setOutputResizeGrip(rect) {
		const gripDistance = 20;
		this.outputResizeL.style.left = `${rect.x - this.outputResizeGripDistance}px`;
		this.outputResizeL.style.top = `${rect.y + ((rect.height - this.outputResizeGripLongSize) / 2)}px`;
		this.outputResizeR.style.left = `${rect.x + rect.width + this.outputResizeGripDistance - this.outputResizeGripShortSize}px`;
		this.outputResizeR.style.top = `${rect.y + ((rect.height - this.outputResizeGripLongSize) / 2)}px`;
		this.outputResizeT.style.left = `${rect.x + (rect.width - this.outputResizeGripLongSize) / 2}px`;
		this.outputResizeT.style.top = `${rect.y - this.outputResizeGripDistance}px`;
		this.outputResizeB.style.left = `${rect.x + (rect.width - this.outputResizeGripLongSize) / 2}px`;
		this.outputResizeB.style.top = `${rect.y + rect.height + this.outputResizeGripDistance - this.outputResizeGripShortSize}px`;
		this.outputResizeL.style.visibility = 'visible';
		this.outputResizeR.style.visibility = 'visible';
		this.outputResizeT.style.visibility = 'visible';
		this.outputResizeB.style.visibility = 'visible';
	}
	setImageResizeGrip(rect) {
		const halfWidth = this.imageResizeGripSize / 2;
		this.imageResizeTL.style.left = `${rect.x - halfWidth}px`;
		this.imageResizeTL.style.top = `${rect.y - halfWidth}px`;
		this.imageResizeTR.style.left = `${rect.x + rect.width - halfWidth}px`;
		this.imageResizeTR.style.top = `${rect.y - halfWidth}px`;
		this.imageResizeBL.style.left = `${rect.x - halfWidth}px`;
		this.imageResizeBL.style.top = `${rect.y + rect.height - halfWidth}px`;
		this.imageResizeBR.style.left = `${rect.x + rect.width - halfWidth}px`;
		this.imageResizeBR.style.top = `${rect.y + rect.height - halfWidth}px`;
		this.imageResizeTL.style.visibility = 'visible';
		this.imageResizeTR.style.visibility = 'visible';
		this.imageResizeBL.style.visibility = 'visible';
		this.imageResizeBR.style.visibility = 'visible';
	}
	drawBoard(ctx, patternWidth, width, height) {
		const maxY = height / patternWidth + 1;
		const maxX = width / patternWidth + 1;
		for (let y = 0; y < maxY; y++) {
			for (let x = 0; x < maxX; x++) {
				ctx.fillStyle = (y + x) & 1 ? "#F0F0F0" : "white";
				ctx.fillRect(x * patternWidth, y * patternWidth, patternWidth, patternWidth);
			}
		}
	};
	calculateIntersectRect(r1, r2) {
		const leftX   = Math.max(r1.x, r2.x );
		const rightX  = Math.min(r1.x + r1.width, r2.x + r2.width);
		const topY    = Math.max(r1.y, r2.y );
		const bottomY = Math.min(r1.y + r1.height, r2.y + r2.height);

		if (leftX < rightX && topY < bottomY) {
			return {
				x: leftX,
				y: topY,
				width: rightX - leftX,
				height: bottomY - topY
			};
		} else {
			return undefined;
		}
	}
	calculateScreenRect(screenWidth, screenHeight) {
		const maxWidth = this.maxX - this.minX;
		const maxHeight = this.maxY - this.minY;
		let drawWidth = screenWidth;
		let drawHeight = screenHeight;

		if (drawWidth > maxWidth) {
			drawWidth = maxWidth;
			drawHeight = drawWidth / screenWidth * screenHeight;
		}
		
		if (drawHeight > maxHeight) {
			drawHeight = maxHeight;
			drawWidth = drawHeight / screenHeight * screenWidth;
		}

		if (drawWidth < maxWidth && drawHeight < maxHeight) {
			if (this.pointerCaptureId == "outputResizeL" || this.pointerCaptureId == "outputResizeR") {
				drawWidth = maxWidth;
				drawHeight = drawWidth / screenWidth * screenHeight;
			} else if (this.pointerCaptureId == "outputResizeT" || this.pointerCaptureId == "outputResizeB") {
				drawHeight = maxHeight;
				drawWidth = drawHeight / screenHeight * screenWidth;
			} else {
				if (drawWidth > drawHeight) {
					drawWidth = maxWidth;
					drawHeight = drawWidth / screenWidth * screenHeight;
				} else {
					drawHeight = maxHeight;
					drawWidth = drawHeight / screenHeight * screenWidth;
				}
			}
		}

		this.zoomRatio = this.calculateHypotenuse(drawWidth, drawHeight) / this.calculateHypotenuse(this.outputRect.width, this.outputRect.height);

		const x = (maxWidth - drawWidth) / 2 + this.minX;
		const y = (maxHeight - drawHeight) / 2 + this.minY;

		return {
			x: x,
			y: y,
			width: drawWidth,
			height: drawHeight
		};
	}
	calculateHypotenuse(a, b) {
		return Math.sqrt(a * a + b * b);
	}
	realToScreenX(x) {
		return x * this.outputCanvasRect.width / this.outputRect.width;
	}
	realToScreenY(y) {
		return y * this.outputCanvasRect.height / this.outputRect.height;
	}
	screenToRealX(x) {
		return x * this.outputRect.width / this.outputCanvasRect.width;
	}
	screenToRealY(y) {
		return y * this.outputRect.height / this.outputCanvasRect.height;
	}
	changeOutputWidth(width) {
		let drawWidth = this.realToScreenX(width);
		if (drawWidth < 100) {
			drawWidth = 100;
		}
		
		width = this.screenToRealX(drawWidth);
		const diffX = this.realToScreenX(this.outputRect.width - width) / 2;
		const updatedRect = {
			x: this.outputCanvasRect.x + diffX,
			y: this.outputCanvasRect.y,
			width: drawWidth,
			height: this.outputCanvasRect.height
		};

		this.updateOutputCanvasPosition(updatedRect);
		this.updateImageCanvasPosition();
	}
	changeOutputHeight(height) {
		let drawHeight = this.realToScreenX(height);
		if (drawHeight < 100) {
			drawHeight = 100;
		}
		
		height = this.screenToRealX(drawHeight);
		const diffY = this.realToScreenX(this.outputRect.height - height) / 2;
		const updatedRect = {
			x: this.outputCanvasRect.x,
			y: this.outputCanvasRect.y + diffY,
			width: this.outputCanvasRect.width,
			height: drawHeight
		};

		this.updateOutputCanvasPosition(updatedRect);
		this.updateImageCanvasPosition();
	}
	updateOutputCanvasPosition(updatedRect) {
		const initPosition = this.outputCanvasRect == undefined;
		if (initPosition) {
			this.outputCanvasRect = this.calculateScreenRect(this.outputRect.width, this.outputRect.height);
		} else if (updatedRect != undefined) {
			if (updatedRect.width < 100 || updatedRect.height < 100)
				return;

			const screenDiffX = updatedRect.width - this.outputCanvasRect.width;
			const screenDiffY = updatedRect.height - this.outputCanvasRect.height;
			const realDiffX = this.screenToRealX(screenDiffX);
			const realDiffY = this.screenToRealX(screenDiffY);			

			this.outputRect.width += realDiffX;
			this.outputRect.height += realDiffY;

			if (this.pointerCaptureId == "outputResizeL") {
				this.imageRect.x += realDiffX;
			} else if (this.pointerCaptureId == "outputResizeR") {
			} else if (this.pointerCaptureId == "outputResizeT") {
				this.imageRect.y += realDiffY;
			} else if (this.pointerCaptureId == "outputResizeB") {
			}

			this.outputCanvasRect = this.calculateScreenRect(updatedRect.width, updatedRect.height);
		}

		this.outputWidthInput.value = Math.floor(this.outputRect.width);
		this.outputHeightInput.value = Math.floor(this.outputRect.height);

		this.setElementRect(this.outputCanvas, this.outputCanvasRect);
		this.setOutputResizeGrip(this.outputCanvasRect);

		this.drawBoard(this.outputContext, 20, this.outputCanvasRect.width, this.outputCanvasRect.height);
	}
	updateImageCanvasPosition(updatedRect) {
		self = this;

		if (updatedRect != undefined) {
			this.imageRect.x = this.screenToRealX(updatedRect.x - this.outputCanvasRect.x);
			this.imageRect.y = this.screenToRealY(updatedRect.y - this.outputCanvasRect.y);
			this.imageRect.width = this.screenToRealX(updatedRect.width);
			this.imageRect.height = this.screenToRealY(updatedRect.height);
		}

		const x = this.outputCanvasRect.x + this.realToScreenX(this.imageRect.x);
		const y = this.outputCanvasRect.y + this.realToScreenY(this.imageRect.y);
		const drawWidth = this.realToScreenX(this.imageRect.width);
		const drawHeight = this.realToScreenY(this.imageRect.height);
		
		const rect = {
			x: x,
			y: y,
			width: drawWidth,
			height: drawHeight
		};

		if (this.imageCanvasRect == undefined ||
			rect.x != this.imageCanvasRect.x ||
			rect.y != this.imageCanvasRect.y ||
			rect.width != this.imageCanvasRect.width ||
			rect.height != this.imageCanvasRect.height) {
				
			this.setElementRect(this.imageCanvas, rect);
			this.setElementRect(this.maskCanvas, rect);
			this.setImageResizeGrip(rect);
			this.imageCanvasRect = rect;

			this.maskContext.drawImage(this.imageMaskCanvas, 0, 0, rect.width, rect.height);
		}

		this.imageContext.save();
		this.imageContext.clearRect(0, 0, this.imageCanvasRect.width, this.imageCanvasRect.height);

		const intersectRect = this.calculateIntersectRect(this.outputRect, this.imageRect);
		if (intersectRect != undefined) {
			const clipRect = {
				x: this.realToScreenX(intersectRect.x) - this.realToScreenX(this.imageRect.x),
				y: this.realToScreenX(intersectRect.y) - this.realToScreenX(this.imageRect.y),
				width: this.realToScreenX(intersectRect.width),
				height: this.realToScreenX(intersectRect.height),
			}
	
			let region = new Path2D();
			region.rect(clipRect.x, clipRect.y, clipRect.width, clipRect.height);
			this.imageContext.clip(region);
		}

		this.imageContext.drawImage(this.image, 0, 0, this.imageCanvasRect.width, this.imageCanvasRect.height);
		this.imageContext.restore();
	}
	invalidateCanvas(mask_image) {
		this.updateOutputCanvasPosition();
		this.updateImageCanvasPosition();

		prepare_mask(mask_image, this.maskCanvas, this.maskContext, this.getMaskColor());
	}
	async setImages() {
		let self = this;
		this.imageContext.clearRect(0, 0, this.imageCanvas.width, this.imageCanvas.height);
		this.maskContext.clearRect(0, 0, this.maskCanvas.width, this.maskCanvas.height);
		const filepath = ComfyApp.clipspace.images;
		const alpha_url = new URL(
			ComfyApp.clipspace.imgs[ComfyApp.clipspace["selectedIndex"]].src
		);
		alpha_url.searchParams.delete("channel");
		alpha_url.searchParams.delete("preview");
		alpha_url.searchParams.set("channel", "a");
		let mask_image = await loadImage(alpha_url);
		const rgb_url = new URL(
			ComfyApp.clipspace.imgs[ComfyApp.clipspace["selectedIndex"]].src
		);
		rgb_url.searchParams.delete("channel");
		rgb_url.searchParams.set("channel", "rgb");
		this.image = new Image();
		this.image.onload = function () {
			if (self.is_layout_created) {
				self.imageMaskCanvas = document.createElement("canvas");
				self.imageMaskCanvas.id = "imageMaskCanvas";
				self.imageMaskCanvas.width = self.image.width;
				self.imageMaskCanvas.height = self.image.height;
				self.imageMaskCanvas.style.visibility = "hidden";
				self.imageMaskCanvasContext = self.imageMaskCanvas.getContext("2d", { willReadFrequently: true });
			} else {
				self.imageMaskCanvas.width = self.image.width;
				self.imageMaskCanvas.height = self.image.height;
				self.imageMaskCanvasContext.clearRect(0, 0, self.image.width, self.image.height);
			}
			
			self.minX = 190 + self.outputMargin;
			self.minY = 20 + self.outputMargin;
			self.maxX = self.element.clientWidth - 20 - self.outputMargin;
			self.maxY = self.element.clientHeight - 20 - self.outputMargin;

			self.outputRect = {
				x: 0,
				y: 0,
				width: self.image.width,
				height: self.image.height
			};
			self.outputCanvasRect = undefined;

			self.imageRect = self.copyRect(self.outputRect);
			self.imageRatio = self.image.width / self.image.height;

			self.outputWidthInput.value = self.image.width;
			self.outputHeightInput.value = self.image.height;
			self.invalidateCanvas(mask_image);
		};
		this.image.src = rgb_url.toString();
	}
	setEventHandler(maskCanvas) {
		const self = this;
		if (!this.handler_registered) {
			maskCanvas.addEventListener("contextmenu", (event) => {
				event.preventDefault();
			});
			this.element.addEventListener(
				"wheel",
				(event) => this.handleWheelEvent(self, event)
			);
			this.element.addEventListener(
				"pointermove",
				(event) => this.pointMoveEvent(self, event)
			);
			this.element.addEventListener(
				"touchmove",
				(event) => this.pointMoveEvent(self, event)
			);
			this.element.addEventListener("dragstart", (event) => {
				if (event.ctrlKey) {
					event.preventDefault();
				}
			});
			maskCanvas.addEventListener(
				"pointerdown",
				(event) => this.handlePointerDown(self, event)
			);
			maskCanvas.addEventListener(
				"pointermove",
				(event) => this.draw_move(self, event)
			);
			maskCanvas.addEventListener(
				"touchmove",
				(event) => this.draw_move(self, event)
			);
			maskCanvas.addEventListener("pointerover", (event) => {
				this.brush.style.display = "block";
			});
			maskCanvas.addEventListener("pointerleave", (event) => {
				this.brush.style.display = "none";
			});
			document.addEventListener("pointerup", MaskEditorExDialog.handlePointerUp);

			document.addEventListener("keydown", (event) => { event.altKey ? this.brush.textContent = "ᜭ" : this.brush.textContent = "+"; });
			document.addEventListener("keyup", (event) => { event.altKey ? this.brush.textContent = "ᜭ" : this.brush.textContent = "+"; });

			this.handler_registered = true;
		}
	}
	getMaskCanvasStyle() {
		if (this.brush_color_mode === "negative") {
			return {
				mixBlendMode: "difference",
				opacity: "1"
			};
		} else {
			return {
				mixBlendMode: "initial",
				opacity: this.brush_opacity
			};
		}
	}
	getMaskColor() {
		if (this.brush_color_mode === "black") {
			return { r: 0, g: 0, b: 0 };
		}
		if (this.brush_color_mode === "white") {
			return { r: 255, g: 255, b: 255 };
		}
		if (this.brush_color_mode === "negative") {
			return { r: 255, g: 255, b: 255 };
		}
		return { r: 0, g: 0, b: 0 };
	}
	getMaskFillStyle() {
		const maskColor = this.getMaskColor();
		return "rgb(" + maskColor.r + "," + maskColor.g + "," + maskColor.b + ")";
	}
	getColorButtonText() {
		let colorCaption = "unknown";
		if (this.brush_color_mode === "black") {
			colorCaption = "black";
		} else if (this.brush_color_mode === "white") {
			colorCaption = "white";
		} else if (this.brush_color_mode === "negative") {
			colorCaption = "negative";
		}
		return "Color: " + colorCaption;
	}
	updateWhenBrushColorModeChanged() {
		this.colorButton.innerText = this.getColorButtonText();
		const maskCanvasStyle = this.getMaskCanvasStyle();
		this.maskCanvas.style.mixBlendMode = maskCanvasStyle.mixBlendMode;
		this.maskCanvas.style.opacity = maskCanvasStyle.opacity.toString();
		const maskColor = this.getMaskColor();
		const maskData = this.maskContext.getImageData(
			0,
			0,
			this.maskCanvas.width,
			this.maskCanvas.height
		);
		for (let i = 0; i < maskData.data.length; i += 4) {
			maskData.data[i] = maskColor.r;
			maskData.data[i + 1] = maskColor.g;
			maskData.data[i + 2] = maskColor.b;
		}
		this.maskContext.putImageData(maskData, 0, 0);
	}
	brush_opacity = 0.7;
	brush_size = 10;
	brush_color_mode = "black";
	drawing_mode = false;
	lastx = -1;
	lasty = -1;
	lasttime = 0;
	static handleKeyDown(event) {
		const self = MaskEditorExDialog.instance;
		if (event.key === "]") {
			self.brush_size = Math.min(self.brush_size + 2, 100);
			self.brush_slider_input.value = self.brush_size;
		} else if (event.key === "[") {
			self.brush_size = Math.max(self.brush_size - 2, 1);
			self.brush_slider_input.value = self.brush_size;
			// } else if (event.key === "Enter") {
			// 	self.save();
		}
		self.updateBrushPreview(self);
	}
	static handlePointerUp(event) {
		event.preventDefault();
		this.mousedown_x = null;
		this.mousedown_y = null;
		MaskEditorExDialog.instance.pointerCaptureId = undefined;
		MaskEditorExDialog.instance.drawing_mode = false;
	}
	updateBrushPreview(self) {
		const brush = self.brush;
		brush.style.width = self.brush_size * 2 + "px";
		brush.style.height = self.brush_size * 2 + "px";
		brush.style.left = self.cursorPoint.x - self.brush_size + "px";
		brush.style.top = self.cursorPoint.y - self.brush_size + "px";
		brush.style.lineHeight = self.brush_size * 2 + "px";

		if (self.brush_size * 2 <= self.maxBrushFontSize)
			brush.style.fontSize = self.brush_size * 2 + "px";
	}
	handleWheelEvent(self, event) {
		event.preventDefault();
		if (event.ctrlKey) {
			if (event.deltaY < 0) {
				this.zoom_ratio = Math.min(10, this.zoom_ratio + 0.2);
			} else {
				this.zoom_ratio = Math.max(0.2, this.zoom_ratio - 0.2);
			}
			// this.invalidatePanZoom();
		} else {
			if (event.deltaY < 0) this.brush_size = Math.min(this.brush_size + 2, 100);
			else this.brush_size = Math.max(this.brush_size - 2, 1);
			this.brush_slider_input.value = this.brush_size.toString();
			this.updateBrushPreview(this);
		}
	}
	pointMoveEvent(self, event) {
		self.cursorPoint = { x: event.pageX, y: event.pageY };

		if (["imageResizeTL", "imageResizeTR", "imageResizeBL", "imageResizeBR"].includes(self.pointerCaptureId)) {
			const offsetX = self.cursorPoint.x - self.pointerDownPoint.x;
			const offsetY = self.cursorPoint.y - self.pointerDownPoint.y;
			const rect = self.copyRect(self.imageCanvasRect);

			if (self.pointerCaptureId == "imageResizeTL") {
				rect.x += offsetX;
				rect.y += offsetY;
				rect.width -= offsetX;
				rect.height -= offsetY;
	
				const ratioWidth = rect.height * self.imageRatio;
				const ratioOffsetX = rect.width - ratioWidth;
				rect.x += ratioOffsetX;
				rect.width -= ratioOffsetX;
			} else if (self.pointerCaptureId == "imageResizeTR") {
				rect.y += offsetY;
				rect.width -= offsetX;
				rect.height -= offsetY;
	
				const ratioWidth = rect.height * self.imageRatio;
				const ratioOffsetX = rect.width - ratioWidth;
				rect.width -= ratioOffsetX;
			} else if (self.pointerCaptureId == "imageResizeBL") {
				rect.x += offsetX;
				rect.width -= offsetX;
				rect.height += offsetY;
	
				const ratioWidth = rect.height * self.imageRatio;
				const ratioOffsetX = rect.width - ratioWidth;
				rect.x += ratioOffsetX;
				rect.width -= ratioOffsetX;
			} else if (self.pointerCaptureId == "imageResizeBR") {
				rect.width += offsetX;
				rect.height += offsetY;
	
				const ratioWidth = rect.height * self.imageRatio;
				const ratioOffsetX = rect.width - ratioWidth;
				rect.width -= ratioOffsetX;
			}

			if (rect.width < 100)
				return;
			
			self.updateOutputCanvasPosition();
			self.updateImageCanvasPosition(rect);

			self.pointerDownPoint.x = self.cursorPoint.x;
			self.pointerDownPoint.y = self.cursorPoint.y;
			return;
		} else if (["outputResizeL", "outputResizeR", "outputResizeT", "outputResizeB"].includes(self.pointerCaptureId)) {
			const offsetX = self.cursorPoint.x - self.pointerDownPoint.x;
			const offsetY = self.cursorPoint.y - self.pointerDownPoint.y;
			const rect = self.copyRect(self.outputCanvasRect);

			if (self.pointerCaptureId == "outputResizeL") {
				rect.x += offsetX;
				rect.width -= offsetX * 2;
			} else if (self.pointerCaptureId == "outputResizeR") {
				rect.x -= offsetX;
				rect.width += offsetX * 2;
			} else if (self.pointerCaptureId == "outputResizeT") {
				rect.y += offsetY;
				rect.height -= offsetY * 2;
			} else if (self.pointerCaptureId == "outputResizeB") {
				rect.y -= offsetY;
				rect.height += offsetY * 2;
			}

			self.updateOutputCanvasPosition(rect);
			self.updateImageCanvasPosition();

			self.pointerDownPoint.x = self.cursorPoint.x;
			self.pointerDownPoint.y = self.cursorPoint.y;
			return;
		}

		self.updateBrushPreview(self);
		if (event.ctrlKey) {
			event.preventDefault();
			self.pan_move(self, event);
		}
		let left_button_down = window.TouchEvent && event instanceof TouchEvent || event.buttons == 1;
		if (event.shiftKey && left_button_down) {
			self.drawing_mode = false;
			const y = event.clientY;
			let delta = (self.zoom_lasty - y) * 5e-3;
			self.zoom_ratio = Math.max(
				Math.min(10, self.last_zoom_ratio - delta),
				0.2
			);
			// this.invalidatePanZoom();
			return;
		}
	}
	eraseImageMask(x, y, brushSize) {
		const ratio = this.imageMaskCanvas.width / this.maskCanvas.width;
		const imageMaskX = x * ratio;
		const imageMaskY = y * ratio;
		const imageMaskBrushSize = brushSize * ratio;
		this.imageMaskCanvasContext.beginPath();
		this.imageMaskCanvasContext.fillStyle = this.getMaskFillStyle();
		this.imageMaskCanvasContext.globalCompositeOperation = "source-over";
		this.imageMaskCanvasContext.arc(imageMaskX, imageMaskY, imageMaskBrushSize, 0, Math.PI * 2, false);
		this.imageMaskCanvasContext.fill();
	}
	restoreImageMask(x, y, brushSize) {
		const ratio = this.imageMaskCanvas.width / this.maskCanvas.width;
		const imageMaskX = x * ratio;
		const imageMaskY = y * ratio;
		const imageMaskBrushSize = brushSize * ratio;
		this.imageMaskCanvasContext.beginPath();
		this.imageMaskCanvasContext.globalCompositeOperation = "destination-out";
		this.imageMaskCanvasContext.arc(imageMaskX, imageMaskY, imageMaskBrushSize, 0, Math.PI * 2, false);
		this.imageMaskCanvasContext.fill();
	}
	draw_move(self, event) {
		if (self.pointerCaptureId != undefined)
			return;

		if (event.ctrlKey || event.shiftKey)
			return;

		event.preventDefault();

		self.cursorPoint = { x: event.pageX, y: event.pageY };
		
		self.updateBrushPreview(self);
		let left_button_down = window.TouchEvent && event instanceof TouchEvent || event.buttons == 1;
		let right_button_down = [2, 5, 32].includes(event.buttons);
		if (!event.altKey && left_button_down) {
			var diff = performance.now() - self.lasttime;
			const maskRect = self.maskCanvas.getBoundingClientRect();
			var x = event.offsetX;
			var y = event.offsetY;
			if (event.offsetX == null) {
				x = event.targetTouches[0].clientX - maskRect.left;
			}
			if (event.offsetY == null) {
				y = event.targetTouches[0].clientY - maskRect.top;
			}
			var brush_size = this.brush_size;
			if (event instanceof PointerEvent && event.pointerType == "pen") {
				brush_size *= event.pressure;
				this.last_pressure = event.pressure;
			} else if (window.TouchEvent && event instanceof TouchEvent && diff < 20) {
				brush_size *= this.last_pressure;
			} else {
				brush_size = this.brush_size;
			}
			if (diff > 20 && !this.drawing_mode)
				requestAnimationFrame(() => {
					self.maskContext.beginPath();
					self.maskContext.fillStyle = this.getMaskFillStyle();
					self.maskContext.globalCompositeOperation = "source-over";
					self.maskContext.arc(x, y, brush_size, 0, Math.PI * 2, false);
					self.maskContext.fill();
					self.eraseImageMask(x, y, brush_size);
					self.lastx = x;
					self.lasty = y;
				});
			else
				requestAnimationFrame(() => {
					self.maskContext.beginPath();
					self.maskContext.fillStyle = this.getMaskFillStyle();
					self.maskContext.globalCompositeOperation = "source-over";
					var dx = x - self.lastx;
					var dy = y - self.lasty;
					var distance = Math.sqrt(dx * dx + dy * dy);
					var directionX = dx / distance;
					var directionY = dy / distance;
					for (var i = 0; i < distance; i += 5) {
						var px = self.lastx + directionX * i;
						var py = self.lasty + directionY * i;
						self.maskContext.arc(px, py, brush_size, 0, Math.PI * 2, false);
						self.maskContext.fill();
						self.eraseImageMask(px, py, brush_size);
					}
					self.lastx = x;
					self.lasty = y;
				});
			self.lasttime = performance.now();
		} else if (event.altKey && left_button_down || right_button_down) {
			const maskRect = self.maskCanvas.getBoundingClientRect();
			const x = (event.offsetX || event.targetTouches[0].clientX - maskRect.left);
			const y = (event.offsetY || event.targetTouches[0].clientY - maskRect.top);
			var brush_size = this.brush_size;
			if (event instanceof PointerEvent && event.pointerType == "pen") {
				brush_size *= event.pressure;
				this.last_pressure = event.pressure;
			} else if (window.TouchEvent && event instanceof TouchEvent && diff < 20) {
				brush_size *= this.last_pressure;
			} else {
				brush_size = this.brush_size;
			}
			if (diff > 20 && !this.drawing_mode)
				requestAnimationFrame(() => {
					self.maskContext.beginPath();
					self.maskContext.globalCompositeOperation = "destination-out";
					self.maskContext.arc(x, y, brush_size, 0, Math.PI * 2, false);
					self.maskContext.fill();
					self.restoreImageMask(x, y, brush_size);
					self.lastx = x;
					self.lasty = y;
				});
			else
				requestAnimationFrame(() => {
					self.maskContext.beginPath();
					self.maskContext.globalCompositeOperation = "destination-out";
					var dx = x - self.lastx;
					var dy = y - self.lasty;
					var distance = Math.sqrt(dx * dx + dy * dy);
					var directionX = dx / distance;
					var directionY = dy / distance;
					for (var i = 0; i < distance; i += 5) {
						var px = self.lastx + directionX * i;
						var py = self.lasty + directionY * i;
						self.maskContext.arc(px, py, brush_size, 0, Math.PI * 2, false);
						self.maskContext.fill();
						self.restoreImageMask(px, py, brush_size);
					}
					self.lastx = x;
					self.lasty = y;
				});
			self.lasttime = performance.now();
		}
	}
	handlePointerDown(self, event) {
		if (self.pointerCaptureId != undefined)
			return;
			
		var brush_size = this.brush_size;
		if (event instanceof PointerEvent && event.pointerType == "pen") {
			brush_size *= event.pressure;
			this.last_pressure = event.pressure;
		}
		if ([0, 2, 5].includes(event.button)) {
			self.drawing_mode = true;
			event.preventDefault();
			if (event.shiftKey) {
				self.zoom_lasty = event.clientY;
				self.last_zoom_ratio = self.zoom_ratio;
				return;
			}
			const maskRect = self.maskCanvas.getBoundingClientRect();
			// const x = (event.offsetX || event.targetTouches[0].clientX - maskRect.left) / self.zoom_ratio;
			// const y = (event.offsetY || event.targetTouches[0].clientY - maskRect.top) / self.zoom_ratio;
			const x = (event.offsetX || event.targetTouches[0].clientX - maskRect.left);
			const y = (event.offsetY || event.targetTouches[0].clientY - maskRect.top);
			self.maskContext.beginPath();
			if (!event.altKey && event.button == 0) {
				self.maskContext.fillStyle = this.getMaskFillStyle();
				self.maskContext.globalCompositeOperation = "source-over";
				self.eraseImageMask(x, y, brush_size);
			} else {
				self.maskContext.globalCompositeOperation = "destination-out";
				self.restoreImageMask(x, y, brush_size);
			}
			self.maskContext.arc(x, y, brush_size, 0, Math.PI * 2, false);
			self.maskContext.fill();
			self.lastx = x;
			self.lasty = y;
			self.lasttime = performance.now();
		}
	}
	async save() {
		const backupCanvas = document.createElement("canvas");
		const backupCtx = backupCanvas.getContext("2d", {
			willReadFrequently: true
		});
		backupCanvas.width = this.image.width;
		backupCanvas.height = this.image.height;
		backupCtx.clearRect(0, 0, backupCanvas.width, backupCanvas.height);
		backupCtx.drawImage(
			this.maskCanvas,
			0,
			0,
			this.maskCanvas.width,
			this.maskCanvas.height,
			0,
			0,
			backupCanvas.width,
			backupCanvas.height
		);
		const backupData = backupCtx.getImageData(
			0,
			0,
			backupCanvas.width,
			backupCanvas.height
		);
		for (let i = 0; i < backupData.data.length; i += 4) {
			if (backupData.data[i + 3] == 255) backupData.data[i + 3] = 0;
			else backupData.data[i + 3] = 255;
			backupData.data[i] = 0;
			backupData.data[i + 1] = 0;
			backupData.data[i + 2] = 0;
		}
		backupCtx.globalCompositeOperation = "source-over";
		backupCtx.putImageData(backupData, 0, 0);
		const formData = new FormData();
		const filename = "clipspace-mask-" + performance.now() + ".png";
		const item = {
			filename,
			subfolder: "clipspace",
			type: "input"
		};
		if (ComfyApp.clipspace.images) ComfyApp.clipspace.images[0] = item;
		if (ComfyApp.clipspace.widgets) {
			const index = ComfyApp.clipspace.widgets.findIndex(
				(obj) => obj.name === "image"
			);
			if (index >= 0) ComfyApp.clipspace.widgets[index].value = item;
		}
		const dataURL = backupCanvas.toDataURL();
		const blob = dataURLToBlob(dataURL);
		let original_url = new URL(this.image.src);
		const original_ref = {
			filename: original_url.searchParams.get("filename")
		};
		let original_subfolder = original_url.searchParams.get("subfolder");
		if (original_subfolder) original_ref.subfolder = original_subfolder;
		let original_type = original_url.searchParams.get("type");
		if (original_type) original_ref.type = original_type;
		formData.append("image", blob, filename);
		formData.append("original_ref", JSON.stringify(original_ref));
		formData.append("type", "input");
		formData.append("subfolder", "clipspace");
		this.saveButton.innerText = "Saving...";
		this.saveButton.disabled = true;
		await uploadMask(item, formData);
		ComfyApp.onClipspaceEditorSave();
		this.close();
	}
}
//http://127.0.0.1:8188/api/view?filename=clipspace-mask-265435.200000003.png&subfolder=clipspace&type=input&rand=0.5883156726899244
//http://127.0.0.1:8188/view?filename=clipspace-mask-307289.200000003.png&type=input
function addMenuHandler(nodeType, cb) {
	const getOpts = nodeType.prototype.getExtraMenuOptions;
	nodeType.prototype.getExtraMenuOptions = function () {
		const r = getOpts.apply(this, arguments);
		cb.apply(this, arguments);
		return r;
	};
}

app.registerExtension({
	name: "Comfy.FlowControl.MaskEditorEx",
	init(app) {
		const callback =
			function () {
				let dlg = MaskEditorExDialog.getInstance();
				dlg.show();
			};

		const context_predicate = () => ComfyApp.clipspace && ComfyApp.clipspace.imgs && ComfyApp.clipspace.imgs.length > 0
		ClipspaceDialog.registerButton("MaskEditorEx", context_predicate, callback);
	},

	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (Array.isArray(nodeData.output) && (nodeData.output.includes("MASK") || nodeData.output.includes("IMAGE"))) {
			addMenuHandler(nodeType, function (_, options) {
				options.unshift({
					content: "Open in MaskEditorEx",
					callback: () => {
						ComfyApp.copyToClipspace(this);
						ComfyApp.clipspace_return_node = this;

						let dlg = MaskEditorExDialog.getInstance();
						dlg.show();
					},
				});
			});
		}
	}
});