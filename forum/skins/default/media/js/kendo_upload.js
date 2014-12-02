function kendo_upload_init(filesJson,upload_files_selector,attachment_token_selector, saveUrl, removeUrl)
{
    var $upload = upload_files_selector;
    var allowMultiple = Boolean($upload.attr("multiple"));
    var upload = $upload.kendoUpload({
    async: {
        saveUrl: saveUrl,
        removeUrl: removeUrl
    },
    error: onError,
    success: onSuccess,
    upload: function(e){
            e.data = {token : attachment_token_selector.val()};
        },
    remove: function(e){
            e.data = {token : attachment_token_selector.val()};
        }
    }).getKendoUpload();

    if (upload) {
        filesJson = eval(filesJson);
        if (filesJson != null && filesJson.length > 0) {                
            $.map(filesJson, function (item,index) {
                var name = item.name + " [ "+ item.size/1000.0 +" KB ]";
                var sourceInput = upload._module.element.find("input[type='file']").last();
                upload._addInput(sourceInput.clone().val(""));
                var file = upload._enqueueFile(name, {
                    relatedInput : sourceInput,
                    fileNames : [filesJson[index]]
                });
                upload._fileAction(file, "remove");
            });
            $("span.k-icon").addClass("k-success");
            $("span.k-filename").attr("style","width:100%");
        }
    }
}

function onSuccess(e) {
    $("span.k-filename").attr("style","width:100%");
    if(e.response.status == "error"){
        alert(e.response.message);
        if($(".k-upload-files.k-reset").find("li").length == 1){
            $(".k-upload-files.k-reset").find("li").parent().remove();
        }else{
            $(".k-upload-files.k-reset li.k-file span.k-filename[title='"+e.files[0]['name']+"']" ).parent().last().remove();
        }
    }else if(e.response.status == "delete"){
        $("#id_form_attachments").val($("#id_form_attachments").val().replace(e.response.filename,''));
        $("#id_form_attachments").val($("#id_form_attachments").val().replace(';;',';'));
    }else{
        update_file = $(".k-upload-files.k-reset .k-file span.k-filename[title='"+e.files[0]['name']+"']").last();
        update_file.text(e.response.filename + " [ " + e.response.filesize/1000.0 + " KB ] ");
        update_file.attr("title",e.response.filename);
        e.files[0]['name'] = e.response.filename;
        $("#id_form_attachments").val(e.response.filename+";"+$("#id_form_attachments").val());
    }
}
function onError(e) {
    alert('Error occured');
}
            
