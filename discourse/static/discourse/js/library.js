$(function() {
    var library = null;

    $('.library').each(function(i, e) {
        library = Library({source: $(e)});
    });

    if (library) {
        var toolup = LibraryToolup({library: library});

        $(document).on('click', '.attach', function(e) {
            toolup.go($(this));
            e.preventDefault();
            return false;
        });
    }
});

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
    url: null,
    editable: true,
    init : function() {
        this.__super__();

        this.iconMap = {};
        this.path = this.path || this.source.attr('path');
        this.url = this.url || this.source.attr('url');

        this.scrapeValue();
        this.build();
        this.setValue(this.value);

        if (this.editable)
            this.source.addClass('editable');

        //this.hook(discourse, 'attachment', this.changeFile(data));
        //discourse.follow(this.path);
    },
    changeFile : function(file) {
        this.addIcon(file);
        this.fixButtons();
    },
    scrapeValue : function() {
        var value = [];

        this.source.find('li a').each(function(i, e) {
            var link = $(e);
            var mimetype = link.attr('mimetype');
            if (!mimetype) return;

            value.push({
                url: link.attr('href'),
                path: link.attr('path'),
                icon: link.attr('icon'),
                hidden: link.hasClass('hidden'),
                content_type: mimetype,
                filename: link.find('.text').html()
            });
        });

        this.value = value;
    },
    build : function() {
        this.source.empty();

        this.title = $('<div class="title">').append('Materials').appendTo(this.source);
        this.content = $('<ul class="list content">').appendTo(this.source);
        this.actions = $('<div class="actions">').appendTo(this.source);

        this.actions.download = $('<a class="action download"><span></span>Download</a>').appendTo(this.actions);
        this.actions.hide = $('<a class="action hide"><span></span>Hide</a>').appendTo(this.actions);
        this.actions.show = $('<a class="action hide"><span></span>Show</a>').appendTo(this.actions);
        this.actions.del = $('<a class="action delete"><span></span>Delete</a>').appendTo(this.actions);

        this.hook(this.actions.download, 'click', this.manipulator('zip'));
        this.hook(this.actions.hide, 'click', this.manipulator('hide', function(icon) { icon.setFileHidden(true); }));
        this.hook(this.actions.show, 'click', this.manipulator('show', function(icon) { icon.setFileHidden(false); }));
        this.hook(this.actions.del, 'click', this.manipulator('delete', function(icon) { icon.destroy(); }));

        this.insertInto = this.adder;

        if (this.editable) {
            this.adder = $('<li class="add">')
                .appendTo(this.content)
                .append('<a href="#">+<input type="file" name="upload[]" multiple="multiple" id="library-upload"></a>');
            this.insertBefore = this.adder;
        } else {
            this.insertInto = this.content;
        }

        setupFileDrop(this);
    },
    setValue : function(value) {
        for(var i = 0; i < value.length; i++) {
            var file = value[i];
            this.addIcon(file);
        }
    },
    findIcon : function(url) {
        this.each(function(i, item) {
            if (item.url == url) return item;
        });
        return null;
    },
    addIcon : function(file) {
        var icon = this.iconMap[file.url];
        if (icon) {
            icon.setValue(file);
            return icon;
        }
     
        var icon = LibraryIcon({value: file, selectable: this.editable});
        this.append(icon);
        this.iconMap[file.url] = icon;
        return icon;
    },
    select : function(icon, e) {
        if (e && (e.shiftKey || e.metaKey || e.altKey || e.ctrlKey)) {
            icon.setSelected(!icon.selected);
            var selected = this.selected = [];
            this.each(function(i, other) {
                if (other.selected) 
                    selected.push(other);
            });
            return this.fixButtons();
        }
        
        this.each(function(i, other) {
            if (icon != other)
                other.setSelected(false);
        });

        if (icon) {
            icon.setSelected(true);
            this.selected = [icon];
        } else {
            this.selected = [];
        }

        this.fixButtons();
    },
    fixButtons : function() {
        if (this.items.length == 0) {
            this.actions.download.addClass('disabled');
        } else {
            this.actions.download.removeClass('disabled');
        }

        if (this.selected.length == 0) {
            this.actions.hide.hide();
            this.actions.show.hide();
            this.actions.del.hide();
            this.actions.download.empty().append('Download All');
        } else {
            this.actions.del.show();
            this.actions.download.empty().append('Download');

            var visible = 0;
            this.each(function(i, item) {
                if (item.selected && !item.value.hidden)
                    visible += 1;
            });

            if (visible > 0) {
                this.actions.hide.show();
                this.actions.show.hide();
            } else {
                this.actions.hide.hide();
                this.actions.show.show();
            }
        }
    },
    onDownload : function() {
        if (this.selected.length == 0) return;


    },
    manipulator : function(method, fn) {
        return function() {
            if (this.selected.length == 0) {
                if (method == 'zip')
                    this.selectAll();
                else
                    return;
            }

            var paths = [];
            for(var i = 0; i < this.selected.length; i++) {
                if (fn)
                    fn(this.selected[i]);
                paths.push(this.selected[i].value.path);
            }

            this.fixButtons();

            jQuery.ajax({
                url: this.url,
                type: 'POST',
                data: {method: method, paths: paths},
                context: this,
                error: function() {
                    Overlay.status.error("File Management", "Server error.");
                },
                success: function(response) {
                    if (method == 'zip') {
                        this.poll_download(response);
                    } else {
                        Overlay.status.confirm("File Management", "Success!");
                    }
                }
            });
        }
    },
    selectAll : function() {
        this.each(function(i, item) {
            item.setSelected(true);
        });
        this.selected = this.items.slice();
    },
    check_download : function(zipinfo) {
        if (zipinfo.status == 'ready') {
            Overlay.status.progress("Archiving...", 1);
            window.open(zipinfo.url);
        } else if (zipinfo.status == 'working') {
            Overlay.status.progress("Archiving...", .5);
            this.poll_download_soon(zipinfo, 1000);
        } else {
            Overlay.status.error("Server Error", "Unnable to create zip of attachments.");
        }
    },
    poll_download : function(zipinfo) {
        jQuery.ajax({
            url: zipinfo.url + "?poll",
            success: this.check_download,
            error: function() { this.poll_download_soon(zipinfo, 2000) },
            context: this
        })
    },
    poll_download_soon : function(zipinfo, delay) {
        var self = this;

        setTimeout(function() { self.poll_download(zipinfo) }, delay);
    }
});

LibraryIcon = Tea.Element.extend({
    source: '<li>',
    type: 'library-icon',
    cls: 'icon',
    value: null,
    selected: false,
    selectable: true,
    render : function() {
        this.__super__();
        this.link = $('<a target="_blank">').appendTo(this.source);
        this.icon = $('<div>').addClass('icon').appendTo(this.link);
        this.text = $('<div>').addClass('text').appendTo(this.link);

        if (this.selectable)
            this.hook(this.source, 'click', function(e) {
                this._parent.select(this, e)
                e.preventDefault();
            })
    },
    setValue : function(file) {
        this.link.attr('href', file.url);
        this.text.empty().append(file.filename);
        this.icon.attr('class', 'icon').addClass('icon-' + file.icon);
        if (file.hidden) {
            this.source.addClass('hidden');
        } else {
            this.source.removeClass('hidden');
        }
    },
    setSelected : function(toggle) {
        this.selected = toggle;
        if (toggle) 
            this.source.addClass('selected');
        else
            this.source.removeClass('selected');
    },
    select : function() {
        this.setSelected(true);
    },
    unselect : function() {
        this.setSelected(false);
    },
    setFileHidden : function(t) {
        this.value.hidden = t;
        if (t) {
            this.source.addClass('hidden');
        } else {
            this.source.removeClass('hidden');
        }
    }
});


function setupFileDrop(library) {
    $(document.body).filedrop({
        fallback_id: 'library-upload',    // an identifier of a standard file input element
        url: library.url,                // upload handler, handles each file separately, can also be a function returning a url
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

            library.changeFile(attachment);
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