/**
 * Must be included on forms that use the TiledFileSelectWidget class.
 */

import { DynamicSubscriberManager } from './utils/events'
import { expectQuerySelector, htmlElementQuerySelectAll } from './utils/timing'

const initWidget = (widgetContainer: HTMLElement) => {
    
    const widget = expectQuerySelector(widgetContainer, ".tiled-foreignkey-widget")
    const modal = expectQuerySelector(widgetContainer, ".upload-modal");

    const fileInput = expectQuerySelector(modal, ".icon-file-input") as HTMLInputElement;
    const previewContainer = expectQuerySelector(modal, '.preview-container') as HTMLDivElement;
    const previewImage = expectQuerySelector(modal, '.preview-image') as HTMLImageElement;
    const uploadBtn = expectQuerySelector(modal, '.upload-btn') as HTMLButtonElement;
    const cancelBtn = expectQuerySelector(modal, '.cancel-btn') as HTMLButtonElement;
    const uploadStatus = expectQuerySelector(modal, '.upload-status');
    const uploadTile = expectQuerySelector(widget, ".upload-tile");

    function onTileClick (this: HTMLElement, _: PointerEvent | null): any {
        // Add selected attribute to this tile and remove from all others
        widget.querySelectorAll('.tile').forEach(t => t.classList.remove('selected'));
        this.classList.add('selected');
        if (this.dataset.value !== undefined){
            // Update hidden select options to reflect that this tile has been selected
            const hiddenSelect = expectQuerySelector(widget, ".tiled-fk-select") as HTMLInputElement;
            hiddenSelect.value = this.dataset.value;
        }
    };

    function openModal (): void {
        modal.style.display = 'block';
    }

    function closeModal (): void {
        modal.style.display = 'none';
        fileInput.value = '';
        previewContainer.style.display = 'none';
        uploadStatus.textContent = '';
    }

    const registerEventListeners = () => {

        // Clicking on tiles selects them in the form.
        const initialTiles =  htmlElementQuerySelectAll(widget, ".tile:not(.upload-tile)");
        for (let tile of initialTiles){
            tile.addEventListener("click", onTileClick);
        }

        // Open the modal when the "upload-tile" is clicked.
        uploadTile.addEventListener('click', openModal);

        // Close the modal when "Cancel" is clicked.
        cancelBtn.addEventListener('click', closeModal);

    };
    registerEventListeners();

    // Add a preview when a new image-file is uploaded
    fileInput.addEventListener('change', (fileChangedEvent) => {
        if (
            fileChangedEvent.target === null || 
            !(fileChangedEvent.target instanceof HTMLInputElement) || 
            !fileChangedEvent.target.files
        ){
            return;
        }
        const file = fileChangedEvent.target.files[0];
        if (file) {

            // If a file is changed
            const reader = new FileReader();
            reader.onload = (postFileReadEvent) => {
                if (
                    postFileReadEvent.target === null || 
                    postFileReadEvent.target.result === null || 
                    postFileReadEvent.target.result instanceof ArrayBuffer
                ){
                    return;
                }
                // Set the preview image src to the file's URL
                previewImage.src = postFileReadEvent.target.result;
                previewContainer.style.display = 'block';
            };

            // Trigger file-read/load when the file is changed
            reader.readAsDataURL(file);
        }
    });

    // Handle upload button
    uploadBtn.addEventListener('click', async () => {

        // Exit early if no file was selected
        if (fileInput.files === null || fileInput.files[0] == null){
            uploadStatus.textContent = 'Please select a file';
            return;
        }
        const file = fileInput.files[0];

        // Prevent multiple submission clicks
        if (uploadBtn.disabled) {
            return;
        }

        // Get CSRF token
        const csrfToken = (expectQuerySelector(document, '[name=csrfmiddlewaretoken]') as HTMLInputElement).value;

        uploadStatus.textContent = 'Uploading...';
        uploadBtn.disabled = true;
        cancelBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch('/rush/icon/ajax-upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                // Add new tile to the widget
                const newTile = document.createElement('div');
                newTile.className = 'tile selected';
                newTile.dataset.value = data.id;
                newTile.innerHTML = `<img src="${data.url}" alt="">`;

                // Insert before upload tile
                const uploadTile = widget.querySelector('.upload-tile');
                widget.insertBefore(newTile, uploadTile);

                // Add to select options
                const hiddenSelect = expectQuerySelector(widget, ".tiled-fk-select") as HTMLInputElement;
                const option = document.createElement('option');
                option.value = data.id;
                option.selected = true;
                hiddenSelect.appendChild(option);

                // Deselect other tiles
                widget.querySelectorAll('.tile').forEach(t => t.classList.remove('selected'));
                newTile.classList.add('selected');

                // Add click handler to new tile
                newTile.addEventListener('click', () => {
                    widget.querySelectorAll('.tile').forEach(t => t.classList.remove('selected'));
                    newTile.classList.add('selected');
                    if (newTile.dataset.value !== undefined){
                        hiddenSelect.value = newTile.dataset.value;
                    }
                });

                // Close modal
                closeModal();

            } else {
                uploadStatus.textContent = 'Error: ' + (data.error || 'Upload failed');
            }
        } catch (error) {
            if (error instanceof Error) {
                uploadStatus.textContent = 'Error: ' + error.message;
            } else {
                uploadStatus.textContent = 'Error: ' + String(error);
            }
        } finally {
            uploadBtn.disabled = false;
            cancelBtn.disabled = false;
        }
    });
};

/**
 * Initialize widgets on page-load, and anytime a widget is added to the form.
 */
document.addEventListener('DOMContentLoaded', () => {

    /**
     * Initialize all widgets that are children of the given parent element.
     * @param parentEl the parent element.
     */
    const initWidgetsInside = (parentEl: HTMLElement) => {
        const addedWidgets = parentEl.querySelectorAll(".tiled-foreignkey-widget-container");
        for (let widget of addedWidgets){
            if (!(widget instanceof HTMLElement)){
                continue;
            }
            initWidget(widget);
        }
    };

    const manager = new DynamicSubscriberManager(document.body)
    manager.subscribeMutationObserver(
        {childList: true, subtree: true}, 
        "form",
        (record: MutationRecord) => {
            for (let node of record.addedNodes){
                if (!(node instanceof HTMLElement)){
                    continue;
                }
                // Try to init when nodes are added to the form. E.g., a new inline
                // row is added to the form, and it may contain a widget.
                initWidgetsInside(node);
            }
        }
    );

    // Try initializing any pre-existing widgets on the initial form load...
    initWidgetsInside(document.body);
});