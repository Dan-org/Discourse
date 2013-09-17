LibraryViewOptions = Tea.Element.extend({
    value: 'list',
    cls: 'view-options',
    init : function() {
        this.__super__();

        if (this.source[0].childNodes.length == 0) {
            this.build();
        }

        this.setValue(this.value);
    },
    build : function() {
        this.source.append('<a class="option option-list">');
        this.source.append('<a class="option option-tile">');
    },
    setValue : function(v) {
        if (!this.listButton) return this.value = v;

        this.source.find('a').removeClass('selected');
        this.source.find('a.option-' + v).addClass('selected');
        this.value = v;
    },
    getValue : function() {
        return this.value;
    }
});

Library = Tea.Container.extend({
    type: 'library',
    cls: 'library',
    path: null,
    init : function() {
        this.__super__();

        this.path = this.path || this.source.attr('path');

        if (this.source[0].childNodes.length > 0) {
            this.retrofit();
        } else {
            this.build();
        }

        this.insertBefore = this.adder;

        this.hook(discourse, 'attachment', this.changeFile(data));
        discourse.follow(this.path);
    },
    changeFile : function(data) {
        if (data.path != this.path) return;
        console.log("File changed", data);
    },
    retrofit : function() {
        this.topbar = this.source.children('topbar');
        this.content = this.source.children('files');

        this.adder = this.content.children('add');
    },
    build : function() {
        this.top = $('<div class="title">').appendTo(this.source);
        this.content = $('<div class="content">').appendTo(this.source);

        this.adder = $('<a class="add" href="#">')
            .appendTo(this.content)
            .append('<input type="file" name="upload[]" multiple="multiple">');

        this.items = [];
        this.content.find('a').each(function(i, e){
            this.own({
                type: 'library-icon',
                source: e,
                _index: i
            })
        });
    }
});

$(function() {
    $('.library').each(function(i, e) {
        Library({source: $(e)});
    });
});

LibraryIcon = Tea.Container.extend({
    type: 'library-icon',
    cls: 'icon',
    icon: null,
    url: null,
    pk: null,
    init : function() {
        this.__super__();

        if (this.source[0].childNodes.length > 0) {
            this.retrofit();
        } else {
            this.build();
        }
    },
    build : function() {

    },
    retrofit : function() {

    }
});


$(function() {
    return;
    Library.retrofit()
    $('.library').each(function() {
        var div = $(this);
        var path = div.attr('url');
        Library({
            source: this
        });
    });

        var self = this;
        var files = this.source.find('a');

        files.each(function(i, item) {
            this.items.push(LibraryIcon({
                source: item,
                mimetype: item.attr('mimetype', 'plain'),
                url: item.attr('href'),
                pk: item.attr('attachment')
            }));
        });


    return;

    var library = $('.library');

    if (library.find('ul li').length == 0) library.hide();

    $(document.body).on('click', '.view-options a', function(e) {
        var a = $(e.currentTarget);
        if (a.hasClass('selected')) return;
        a.closest('.view-options').find('a.selected').removeClass('selected');
        a.addClass('selected');

        var ul = a.closest('.library').find('ul').eq(0);
        if (a.hasClass('option-list')) {
            ul.removeClass('tile').addClass('list');
        } else {
            ul.removeClass('list').addClass('tile');
        }
    })

    // Delete by holding the shift key.
    $(document.body).on('click', 'a', function(e) {
        var a = $(e.currentTarget);
        var li = a.closest('li');
        if (e.shiftKey) {
            jQuery.ajax({
                url: $(a).attr('href'),
                type: 'GET',
                data: {method: 'DELETE'},
                success : function() {
                    li.fadeOut("normal", function() {
                        $(this).remove();
                        if (library.find('ul li').length == 0) library.hide();
                    });
                }
            });
            e.preventDefault();
        }
    });

    if (library.length > 0) {
        $(document.body).filedrop({
            fallback_id: 'library-upload',    // an identifier of a standard file input element
            url: library.attr('url'),         // upload handler, handles each file separately, can also be a function returning a url
            paramname: 'file',                // POST parameter name used on serverside to reference file
            withCredentials: true,            // make a cross-origin request with cookies
            headers: {          // Send additional request headers
                'X-CSRFToken': $.cookie('csrftoken')
            },
            error: function(err, file) {
                switch(err) {
                    case 'BrowserNotSupported':
                        console.log('BrowserNotSupported');
                        break;
                    case 'TooManyFiles':
                        console.log('TooManyFiles');
                        break;
                    case 'FileTooLarge':
                        // program encountered a file whose size is greater than 'maxfilesize'
                        // FileTooLarge also has access to the file which was too large
                        // use file.name to reference the filename of the culprit file
                        console.log('FileTooLarge');
                        break;
                    case 'FileTypeNotAllowed':
                        console.log('FileTypeNotAllowed');
                        // The file type is not in the specified list 'allowedfiletypes'
                    default:
                        break;
                }
            },
            maxfiles: 32,
            maxfilesize: 30,
            dragOver: function() {
                // user dragging files over #dropzone
            },
            dragLeave: function() {
                // user dragging files out of #dropzone
            },
            docOver: function() {
                // user dragging files anywhere inside the browser document window
            },
            docLeave: function() {
                // user dragging files out of the browser document window
            },
            drop: function() {
                Overlay.status.progress("Beggining upload...", 0);
            },
            uploadStarted: function(i, file, len) {
                // a file began uploading
                // i = index => 0, 1, 2, 3, 4 etc
                // file is the actual file of the index
                // len = total files user dropped
            },
            uploadFinished: function(i, file, response, time) {
                var attachment = eval(response);
                if (!attachment) return;

                var found = false;
                library.find('li a').each(function() {
                    if ($(this).attr('attachment') == attachment.id + "") {
                        $(this).fadeOut().fadeIn();
                        found = true;
                    }
                });
                
                if (library.find('ul li').length == 0) library.fadeIn('fast');

                if (!found) {
                    var icon = $('<div>').addClass('icon').addClass('icon-' + attachment.icon);
                    var text = $('<div>').addClass('text').append(attachment.filename);
                    var a = $('<a>').attr({
                        'href': attachment.url,
                        'attachment': attachment.id,
                    }).append(icon).append(text);
                    
                    var li = $('<li>').append(a);

                    library.find('ul li.add').before(li);
                    li.fadeOut().fadeIn();
                }
            },
            progressUpdated: function(i, file, progress) {
                // this function is used for large files and updates intermittently
                // progress is the integer value of file being uploaded percentage to completion
            },
            globalProgressUpdated: function(progress) {
                Overlay.status.progress("Upload progress", progress / 100);
                // progress for all the files uploaded on the current instance (percentage)
                // ex: $('#progress div').width(progress+"%");
            },
            speedUpdated: function(i, file, speed) {
                // speed in kb/s
            },
            rename: function(name) {
                // name in string format
                // must return alternate name as string
            },
            beforeEach: function(file) {
                // file is a file object
                // return false to cancel upload
            },
            beforeSend: function(file, i, done) {
                // file is a file object
                // i is the file index
                // call done() to start the upload
                console.log(file);
                done();
            },
            afterAll: function() {
                Overlay.status.progress("Upload complete.", 1);
                //console.log("uploads complete");
                // runs after all files have been uploaded or otherwise dealt with
            }
        });
    }
});