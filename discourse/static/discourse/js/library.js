/*(function() {}
    function getLibrary(source) {
        return source.closest('.discourse-library').data('library');
    }

    $(document).on('.discourse-library .file .delete', function(e) {
        var target = $(e.target);
        var lib = getLibrary(target);

        lib.del(  );
    });
)//();

*/
Channel = function(id) {
    this.id = id;
}

Channel.prototype.show_attachment_modal = function() {
    FileUploadDialog({url: this.id}).show();
}

$(document).on('click', '.discourse .act-upload', function(e) {
    var channel = new Channel( $(e.target).closest('.discourse').attr('data-channel') );
    channel.show_attachment_modal();

    e.preventDefault();
});


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
    });

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

        this.upload = source.find('.act-upload]');
        this.hide = source.find('.act-hide');
        this.show = source.find('.act-show');
        this.del = source.find('.act-delete');

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

        console.log(file);

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
        data: {
            type: 'attachment'
        },
        headers: {
            'X-CSRFToken': $.cookie('csrftoken')
        },
        error : function(err, file) {
            window.file = file;
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


function libraryManipulate(url, type, id, data, success, error) {
    jQuery.ajax({
        url: url,
        type: 'POST',
        data: {type: type, parent: id, data: data},
        context: this,
        error: function() {
            if (error) {
                error();
            } else {
                Overlay.status.error("File Management", "Server error.");    
            }
        },
        success: function(response) {
            var links = $('#message-' + response.parent);

            links.toggleClass('hidden', response.data.hidden);
            
            if (response.data.deleted) {
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

function findLibrary(channel_id) {
    return $('.discourse.library').filter(function() {
        return $(this).attr('data-channel-id') == channel_id;
    });
}

function realizeAttachment(message) {
    console.log("realizeAttachment", message);
    var stream = findLibrary(message.channel);

    var source = stream.find('*[name=' + message.data.filename_hash + ']');
    console.log(source);
    if (source.length != 0) {
        source.replaceWith(message.html);
        return source;
    }

    stream.find('.file-list').prepend(message['html']);
}