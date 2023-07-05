jQuery(function() {
    // Characters remaining counter
    var start = 0;
    var limit = 300;
    $("#id_description").keyup(function() {
        start = this.value.length
        if (start > limit) {
            return false;
        }
        else if (start == 300) {
            $("#remainingCharacters").html("Characters remaining: " + (limit - start)).css('color', 'red');
        }
        else if (start > 286) {
            $("#remainingCharacters").html("Characters remaining: " + (limit - start)).css('color', 'red');
        }
        else if (start < 300) {
            $("#remainingCharacters").html("Characters remaining: " + (limit - start)).css('color', 'gray');
        }
        else {
            $("#remainingCharacters").html("Characters remaining: " + (limit - start)).css('color', 'gray');
        }
    });

});

// Clear contents in modal form when closed
$("#createPlanModal").on('hidden.bs.modal', function() {
    $('#createPlanModal form')[0].reset();
});

// Allow only letters in field
$("input[name=subdomain], input[name=name]").keyup(function() {
    if (!/^[a-zA-Z _]*$/.test(this.value)) {
        this.value = this.value.split(/[^a-zA-Z _]/).join('');
    }
})

// Convert texts to Lowercase
$("input[name=subdomain]").keyup(function () {
    this.value = this.value.toLowerCase();
});

// Prevent excess whitespace in the field(s)
$("input[name=subdomain], input[name=name], input[name=discord_role_id]").on('keydown', function() {
    var $this = $(this);
    $(this).val($this.val().replace(/(\s{2,})|[^a-zA-Z0-9_']/g, ' ').replace(/^\s*/, ''));
});

// Allow only one word in the field
$("input[name=subdomain]").keyup(function () {
    var subdomain = $("input[name=subdomain]").val().trim();
    var words = subdomain.split(' ');

    if (words.length > 1) {
        alert("Only one word is allowed.");
        // Keep only the first word
        $("input[name=subdomain]").val(words[0]);
    }
});

// Prevent starting whitespace in inputs
$("input[type='text'], textarea").on('keypress', function(e) {
    if (e.which === 32 && !this.value.length)
        e.preventDefault();
});

// Allow only numbers in number field
$("input[name=affiliate_commission], input[name=amount], input[name=interval_count]").keyup(function() {
    if (!/^[0-9]*$/.test(this.value)) {
        this.value = this.value.split(/[^0-9]/).join('');
    }
});

// Prevent starting by Zero in number field
$("input[name=affiliate_commission], input[name=amount], input[name=interval_count]").on("input", function() {
    if(/^0/.test(this.value)) {
        this.value = this.value.replace(/^0/, "")
    }
});
