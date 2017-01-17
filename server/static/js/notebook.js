function renderNotebook(ipynb) {


    var data = JSON.parse(ipynb);
    var notebook = nb.parse(data);
    return notebook.render();
}

function displayNotebooks(ipyFiles) {


}
