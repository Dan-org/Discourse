

$(function() {
    var library = null;
    return;

    $('.library').each(function(i) {
        Library({
            source: $(this),
            url: $(this).attr('rel'),
            controls: $(this).find('.actions'),
            contents: $(this).find('.contents'),
            editable: $(this).attr('editable')
        })
    })

    $('.discourse-library').each(function(i, e) {
        library = Library({source: $(e)});
    });

    if (library) {
        if ($('.attach').length > 0) {
            var toolup = LibraryToolup({library: library});

            $(document).on('click', '.attach', function(e) {
                toolup.go($(this));
                e.preventDefault();
                return false;
            });
        } else {
            library.ready("Attachments");
        }
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

LibraryControls = Tea.Element.extend({
    type: 'library-controls',
    library: null,
    hiddenStates: {
        'none': ['hide', 'show', 'del'],
        'one': [],
        'more': [],
        'hidden': ['hide'],
        'visible': ['show'],
        'editable': ['upload', 'hide', 'show', 'del']
    },
    init : function() {
        this.__super__();

        var source = this.source;

        this.upload = source.find('[name=upload]');
        this.hide = source.find('[name=hide]');
        this.show = source.find('[name=show]');
        this.del = source.find('[name=delete]');

        this.hook(this.hide, 'click', this.library.manipulator('hide', function(icon) { icon.setFileHidden(true); }));
        this.hook(this.show, 'click', this.library.manipulator('show', function(icon) { icon.setFileHidden(false); }));
        this.hook(this.del,  'click', this.library.manipulator('delete', function(icon) { icon.destroy(); }));

        this.upload.append('<input type="file" name="upload[]" multiple="multiple" id="library-upload">');

        this.hook(this.library, 'select', this.showButtons);
    },
    showButtons : function(selected) {
        var hide = [];

        this.source.children().show();

        if (selected.length == 0) {
            hide = hide.concat( this.hiddenStates.none );
        } else if (selected.length == 1) {
            hide = hide.concat( this.hiddenStates.one );
        } else if (selected.length > 1) {
            hide = hide.concat( this.hiddenStates.more );
        }

        var hidden = false;
        var visible = false;
        for(var i = 0; i < selected.length; i++) {
            if (selected[i].getValue().hidden) {
                hidden = true;
            } else {
                visible = true;
            }
        }

        if (hidden && !visible) {
            hide = hide.concat( this.hiddenStates.hidden );
        }
        if (visible && !hidden) {
            hide = hide.concat( this.hiddenStates.visible );   
        }

        if (!this.library.editable) {
            hide = hide.concat( this.hiddenStates.editable );
        }
     
        for(var i = 0; i < hide.length; i++) {
            this[hide[i]].hide();
        }
    }
})

Library = Tea.Container.extend({
    type: 'library',
    cls: 'library',
    url: null,
    editable: true,
    files: null,
    prototype: null,
    contents: null,
    controls: null,
    init : function() {
        this.__super__();

        this.iconMap = {};
        this.archive_zip = null;
        this.insertInto = this.contents;

        if (!this.prototype) {
            if (this.contents.find('.prototype').length) {
                this.prototype = this.contents.find('.prototype').detach().removeClass('prototype');
            } else {
                this.prototype = this.contents.children().first().clone().detach();
            }
        }

        this.setupItems();
        this.controls = this.own({type: 'library-controls', source: this.controls, library: this});

        if (this.editable)
            this.source.addClass('editable');

        this.focus = $('<a href="#">').appendTo(this.source);

        this.hook($(document), 'click', function(e) {
            if ($(e.target).closest('.library').length == 0)
                this.select(null);
        });

        this.select(null);
        setupFileDrop(this);
    },
    setupItems : function() {
        var self = this;
        var items = [];
        this.contents.children().each(function() {
            var icon = self.own({type: 'library-icon', source: $(this)});
            items.push(icon);
            self.iconMap[icon.getValue().url] = icon;
        });
        this.items = items;
    },
    createItem : function(file) {
        var item = this.prototype.clone();
        return item;
    },
    changeFile : function(file) {
        this.addIcon(file);
        this.trigger('select', [this.selected]);
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
     
        var icon = this.append({
            type: 'library-icon', 
            value: file, 
            selectable: this.editable, 
            source: this.prototype.clone()
        });

        this.iconMap[file.url] = icon;
        return icon;
    },
    select : function(icon, e) {
        if (icon && !this.editable) {
            window.open(icon.getValue().url);
        }

        if (e && (e.shiftKey || e.metaKey || e.altKey || e.ctrlKey)) {
            icon.setSelected(!icon.selected);
            var selected = this.selected = [];
            this.each(function(i, other) {
                if (other.selected) 
                    selected.push(other);
            });

        } else {
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
        }
        
        if (this.selected.length) {
            this.focus.focus();
        }
        this.trigger('select', [this.selected]);
    },
    onDownload : function() {
        if (this.selected.length == 0) return;
    },
    manipulator : function(data, fn) {
        return jQuery.proxy(function(e) {
            e.preventDefault();

            if (this.selected.length == 0) {
                return;
            }

            var urls = [];
            for(var i = 0; i < this.selected.length; i++) {
                if (fn)
                    fn(this.selected[i]);
                urls.push(this.selected[i].getValue().url);
            }

            this.trigger('select', [this.selected]);     // Trigger in case icons are hidden.

            jQuery.ajax({
                url: this.url,
                type: 'POST',
                data: data,
                context: this,
                error: function() {
                    Overlay.status.error("File Management", "Server error.");
                },
                success: function(response) {}
            });
        }, this);
    },
    selectAll : function() {
        this.each(function(i, item) {
            item.setSelected(true);
        });
        this.selected = this.items.slice();
    },
    check_download : function(zipinfo) {
        this.archive_zip = zipinfo;

        if (zipinfo.status == 'ready') {
            this.fixButtons();
        } else if (zipinfo.status == 'working') {
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
    },
    setArchiving : function(zipinfo) {
        this.archive_zip = zipinfo;
        this.content.hide();
        this.fixButtons();
        this.poll_download(zipinfo);
    },
    ready : function(name) {
        this.content.show();
        this.archive_zip = null;
        this.select(null);
    }
});

LibraryIcon = Tea.Element.extend({
    source: '<li>',
    type: 'library-icon',
    cls: 'icon',
    value: null,
    selected: false,
    selectable: true,
    init : function() {
        this.__super__();

        if (this.selectable)
            this.hook(this.source, 'click', function(e) {
                this._parent.select(this, e);
                e.preventDefault();
            });

        this.hook(this.source, 'dblclick', function(e) {
            window.open(this.getValue().url);
            e.preventDefault();
        })
    },
    getValue : function() {
        var src = this.source;
        return {
            'url': src.attr('href'),
            'hidden': src.hasClass('hidden'),
            'filename': src.find('div[name=name]').val(),
        }
    },
    setValue : function(file) {
        var src = this.source;

        src.attr('href', file.url);
        src.find('img').attr('title', file.filename);
        src.find('div[name=name]').empty().append(file.filename);
        if (file.hidden)
            src.addClass('hidden');
        else
            src.removeClass('hidden');
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
        if (t) {
            this.source.addClass('hidden');
        } else {
            this.source.removeClass('hidden');
        }
    }
});

function setupFileInput(options) {
    options = $.extend({
        url: options.url,
        paramname: 'attachment',
        withCredentials: true,
        maxfiles: 32,
        maxfilesize: 2000,
        headers: {
            'X-CSRFToken': $.cookie('csrftoken')
        },
        error : function(err, file) {
            alert("Error uploading file - " + err + ": " + file);
        }
    }, options);

    options.uploadFinished = function(i, file, response, time) {
        try {
            var attachment = eval(response);
            if (!attachment) return;
        } catch(e) {
            return;
        }

        if (options.uploadComplete) {
            return options.uploadComplete(i, file, attachment, time);
        }
    }

    options.source.filedrop(options);
}


function libraryManipulate(options) {
    var url = options.url;
    var success = options.success || jQuery.noop();
    var error = options.error;
    var data = options.data;

    jQuery.ajax({
        url: url,
        type: 'POST',
        data: data,
        context: this,
        error: function() {
            if (error) {
                error();
            } else {
                Overlay.status.error("File Management", "Server error.");    
            }
        },
        success: function(response) {
            var links = $('#file-' + response.id);

            links.toggleClass('hidden', response.hidden);

            if (response.deleted) {
                links.fadeOut(400, function() {
                    links.remove();
                });
            }

            if (success)
                success(response);
        }
    });
}

// via: http://stackoverflow.com/a/20732091/201069, thanks Andrew V.
function humanFileSize(size) {
    var i = Math.floor( Math.log(size) / Math.log(1024) );
    return ( size / Math.pow(1024, i) ).toFixed(2) * 1 + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
};

function setupFileDrop(library) {
    $(document.body).filedrop({
        fallback_id: 'library-upload',    // an identifier of a standard file input element
        url: library.url,                // upload handler, handles each file separately, can also be a function returning a url
        paramname: 'file',                // POST parameter name used on serverside to reference file
        withCredentials: true,            // make a cross-origin request with cookies
        headers: {          // Send additional request headers
            'X-CSRFToken': $.cookie('csrftoken')
        },
        maxfiles: 32,
        maxfilesize: 10000,
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
            Overlay.status.progress("Begining upload...", 0);
        },
        uploadStarted: function(i, file, len) {
            // a file began uploading
            // i = index => 0, 1, 2, 3, 4 etc
            // file is the actual file of the index
            // len = total files user dropped
        },
        uploadFinished: function(i, file, response, time) {
            try {
                var attachment = eval(response);
                if (!attachment) return;
            } catch(e) {
                return;
            }

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