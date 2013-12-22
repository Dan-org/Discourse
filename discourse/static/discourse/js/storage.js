/*
    The storage object keeps documents saved and sends them to the server.
*/

Storage = Tea.Class({
    type: 'discourse-storage',
    url: null,
    attribute: null,
    value: null,
    save_timeout: 10000,
    init : function() {
        this.__super__();
        this._saved = this.value;   // Store what's been saved here.
        this._failures = 0;         // Every time save fail, this increments.
        this._timeout = null;       // Store the timeout for save delay
        this._ajax = null;          // Store the xhr here.
    },
    setValue : function(value) {
        this.value = value;
        this.saveSoon(this.save_timeout);
    },
    getValue : function() {
        return this.value;
    },
    cancel : function() {
        // Cancel our timeout / save delay.
        if (this._timeout) {
            clearTimeout(this._timeout);
            this._timeout = null;
        }
        // Cancel our xhr.
        if (this._ajax) {
            this._ajax.abort();
            this._ajax = null;
        }
    },
    saveSoon : function(timeout) {
        if (this.value == this._saved) return;
        if (this._timeout != null) return;
        this._timeout = setTimeout(jQuery.proxy(this.save, this), this.save_timeout);
    },
    save : function() {
        // Cancel any timeouts or ajaxes.
        this.cancel();

        // If what we've already saved is what we're going to save, fuck that.
        if (this.value == this._saved) return;

        // Mark the value as saved.
        this._saved = this.value;

        console.log("storage.value", this.value);

        // Ajax!
        this._ajax = jQuery.ajax({
            url: this.url,
            data: {attribute: this.attribute, value:this.value},
            method: 'post',
            success: jQuery.proxy(this.onSuccess, this),
            error: jQuery.proxy(this.onFailure, this)
        });

        // Trigger an event, yo.
        this.trigger('saving');
    },
    onSuccess : function(value) {
        this._failures = 0;
        this.trigger('success', [value]);
    },
    onFailure : function(xhr, status, error) {
        if (error == 'abort') return;

        this._saved = null;
        this._failures += 1;
        this.saveSoon(this._failures * 5000);
        this.trigger('failure');
    }
});
