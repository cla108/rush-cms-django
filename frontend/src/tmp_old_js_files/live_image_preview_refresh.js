/***
 * This script renders a live-preview of 
 * 
 * TODO: WIP
 */
document.addEventListener("DOMContentLoaded", function () {
    const liveImagePreviewElements = document.querySelectorAll('[id^="live_image_input"]');
    for (let imageEl of liveImagePreviewElements){
        const fieldname = imageEl.id.split("live_image_input_")[1];
        const previewEl = document.getElementById('live_image_preview_' + fieldname);

        const refreshPreview = (event) => {

        };

        imageEl.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewEl.src = e.target.result;
                    previewEl.style.display = 'block';
                }
                reader.readAsDataURL(file);
            } else {
                previewEl.src = '#';
                previewEl.style.display = 'none';
            }
        });
    }
    return;
    const iconUploadEl = document.getElementById('id_marker_icon');
    iconUploadEl.addEventListener('change', function(event) {
        const preview = document.getElementById('preview');
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(file);
        } else {
            preview.src = '#';
            preview.style.display = 'none';
        }
    });
});
