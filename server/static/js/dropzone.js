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
    myDropzone = this; // closure
    submitButton.addEventListener("click", function() {
      myDropzone.processQueue(); // Tell Dropzone to process all queued files.
      swal({
        title: 'Uploading files',
        text: 'Sending to the server. Please wait for confirmation',
        imageUrl: '/static/img/loader.gif',
        showConfirmButton: false,
        timer: 60000,
        })

    })

    // You might want to show the submit button only when
    // files are dropped here:
    this.on("addedfile", function(file) {
      // Show submit button here and/or inform user to click it.
      if (file.fullPath) {
          file.previewElement.getElementsByClassName('dz-filename')[0].innerHTML = "<span data-dz-name>" + file.fullPath + "</span>";
      }
    });
    this.on("error", function(file, message) {
        window.swal('Uh-oh!', message.error || 'There was an error. Try again?' , 'error');
        if (file) {
            this.removeFile(file);
        }
        console.log(message)
    });
    this.on("sending", function(file, xhr, formData) {
        // Will send the filesize along with the file as POST data.
        if(file.fullPath){
            formData.append("fullPath", file.fullPath);
        } else {
            formData.append("fullPath", file.name);
        }
    });
    // Listen to the sendingmultiple event. In this case, it's the sendingmultiple event instead
    // of the sending event because uploadMultiple is set to true.
    this.on("sendingmultiple", function() {
      // Gets triggered when the form is actually being sent.
      // Hide the success button or the complete form.
    });
    this.on('uploadprogress', function (file, progress) {
        console.log('progress');

    });


    this.on("successmultiple", function(files, response) {
      // Gets triggered when the files have successfully been sent.
      // Redirect user or notify of success.
      location.href = response['url'];
      swal("Sent!", "Successfully submitted. Going to submission...", 'success');
    });
    this.on("errormultiple", function(files, response) {
      // Gets triggered when there was an error sending the files.
      // Maybe show form again, and notify user of error
        swal("Error!", message.error || 'There was an error', 'error');
        console.log(response);

    });

  }
};


window.addEventListener("dragenter", function(e)
{
    console.log("Dragging");
});

window.addEventListener("dragleave", function(e)
{
        console.log("Dragging out");
});



}

