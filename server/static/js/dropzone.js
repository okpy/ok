function initDropzone(elem, token) {
    Dropzone.options.myDropzone = {

        // Prevents Dropzone from uploading dropped files immediately
        autoProcessQueue: false,
        uploadMultiple: true,
        addRemoveLinks: true,
        clickable: true,
        parallelUploads: 200,
        maxFiles: 200,
        maxFilesize: 10, // MB
        previewTemplate: document.getElementById('dz-preview-template').innerHTML,
        headers: {
            'X-CSRFToken': token
        },
        init: function() {
            var submitButton = document.querySelector("#dzSubmit")
            $('.dz-hidden-input').attr('webkitdirectory', 'true')
            var myDropzone = this; // closure

            submitButton.addEventListener("click", function() {
                Pace.track( function () {
                    myDropzone.processQueue(); // Tell Dropzone to process all queued files.
                });
            })

            this.on("addedfile", function(file) {
                if (file.fullPath) {
                    file.previewElement.getElementsByClassName('dz-filename')[0].innerHTML = "<span data-dz-name>" + file.fullPath + "</span>";
                }
            });
            this.on("error", function(file, message) {
                window.swal('Uh-oh!', message.error || 'There was an error. Try again?' , 'error');
                if (file) {
                    this.removeFile(file);
                }
                $("#dzSubmit").removeClass('disabled');
            });
            // Listen to the sendingmultiple event. In this case, it's the sendingmultiple event instead
            // of the sending event because uploadMultiple is set to true.
            this.on("sendingmultiple", function(files, xhr, formData) {
                // Gets triggered when the form is actually being sent.
                // Hide the success button or the complete form.
                for (var index in files) {
                    var file = files[index];
                    if(file.fullPath){
                        formData.append("fullPath", file.fullPath);
                    } else {
                        formData.append("fullPath", file.name);
                    }
                }
                $("#dzSubmit").addClass('disabled');
            });

            this.on("successmultiple", function(files, response) {
                // Gets triggered when the files have successfully been sent.
                // Redirect user or notify of success.
                location.href = response['url'];
                    swal("Sent!", "Successfully submitted. Going to submission...", 'success');
            });
            this.on("errormultiple", function(files, response) {
                swal("Error!", response.error || response || 'There was an error', 'error');
                $("#dzSubmit").removeClass('disabled');
            });
    }};

    window.addEventListener("dragenter", function(e)
    {
        $('form#myDropzone').css("border-color", 'rgba(51,122,183, 0.9)');
    });

    window.addEventListener("dragleave", function(e)
    {
        $('form#myDropzone').css("border-color", '');

    });

}

