function initalizeNotebookMarkdown() {
    // Customize the markdown function
    var mdRenderer = window.markdownit({
        html: true
    }).enable('image').use(window.markdownitSanitizer)
                      .use(window.markdownItAnchor, {
                        'permalink': true,

                      })

    nb.markdown = function (text) {
        return mdRenderer.render(text)
    };
    nb.ansi = ansi_up.ansi_to_html
}

function renderNotebook(ipynb) {
    var data = JSON.parse(ipynb);
    var notebook = nb.parse(data);
    return notebook.render();
}

function displayNotebooks(ipyFiles) {
    initalizeNotebookMarkdown();

    for (var ipyFile in ipyFiles) {
      var notebookContainer = document.getElementById(ipyFile + '-notebook');
      notebook = renderNotebook(ipyFiles[ipyFile]);
      while (notebookContainer.hasChildNodes()) {
          notebookContainer.removeChild(notebookContainer.lastChild);
      }
      notebookContainer.appendChild(notebook);
    }
}
