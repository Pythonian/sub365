jQuery(function () {
    // Characters remaining counter
    var start = 0;
    var limit = 300;
    $("#id_description, #id_body").keyup(function () {
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
$("#createPlanModal").on('hidden.bs.modal', function () {
    $('#createPlanModal form')[0].reset();
});

// Allow letters, numbers, space and underscore in field
$("input[name=subdomain], input[name=name]").keyup(function () {
    if (!/^[a-zA-Z0-9 _]*$/.test(this.value)) {
        this.value = this.value.split(/[^a-zA-Z0-9 _]/).join('');
    }
});

// Convert texts to Lowercase
$("input[name=subdomain]").keyup(function () {
    this.value = this.value.toLowerCase();
});

// Prevent excess whitespace in the field(s)
$("input[name=subdomain], input[name=name], input[name=discord_role_id]").on('keydown', function () {
    var $this = $(this);
    $(this).val($this.val().replace(/(\s{2,})|[^a-zA-Z0-9_']/g, ' ').replace(/^\s*/, ''));
});

// Allow only one word in the field
$("input[name=subdomain]").keyup(function () {
    var subdomain = $("input[name=subdomain]").val().trim();
    var words = subdomain.split(' ');

    if (words.length > 1) {
        alert("Only one word is allowed. Use underscore for multiple words.");
        // Keep only the first word
        $("input[name=subdomain]").val(words[0]);
    }
});

// Prevent starting whitespace in inputs
$("input[type='text'], textarea").on('keypress', function (e) {
    if (e.which === 32 && !this.value.length)
        e.preventDefault();
});

// Allow only numbers in number field
$("input[name=affiliate_commission], input[name=amount], input[name=interval_count]").keyup(function () {
    if (!/^[0-9]*$/.test(this.value)) {
        this.value = this.value.split(/[^0-9]/).join('');
    }
});

// Prevent starting by Zero in number field
$("input[name=affiliate_commission], input[name=amount], input[name=interval_count]").on("input", function () {
    if (/^0/.test(this.value)) {
        this.value = this.value.replace(/^0/, "")
    }
});

// Disable the submit button if no changes has been made to the form input
const form = document.querySelectorAll("input, textarea");
for (const data of form) {
    data.saved = data.value;
}
(btnEnabled = function () {
    var btn = true;
    for (const data of form) {
        if (data.saved !== data.value) {
            btn = false;
            break;
        }
    }
    $("#updatePlan, #updatepaymentMethod").prop("disabled", btn);
})();
document.oninput = btnEnabled // Call

var copyButton = document.getElementById("copy-button");
if (copyButton) {
    copyButton.addEventListener("click", function () {
        var textLink = this.getAttribute("data-copy-link");
        var originalText = this.innerHTML; // Save the original button text

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(textLink)
                .then(() => {
                    // Update the button text
                    this.innerHTML = '<i class="fa-solid fa-check me-1"></i> Subscription Link Copied!';

                    // Reset button text after 3 seconds
                    setTimeout(() => {
                        this.innerHTML = originalText;
                    }, 3000);
                })
                .catch((error) => {
                    console.error("Failed to copy link:", error);
                });
        } else {
            // Fallback for browsers that don't support the Clipboard API
            var textarea = document.createElement("textarea");
            textarea.value = textLink;
            textarea.style.position = "fixed";  // Ensure the textarea is visible
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();

            try {
                var successful = document.execCommand("copy");
                if (successful) {
                    this.innerHTML = '<i class="fa-regular fa-clipboard-check me-1"></i> Subscription Link Copied!';
                    this.classList.replace("btn-primary", "btn-success");

                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.classList.replace("btn-success", "btn-primary");
                    }, 3000);
                }
            } catch (error) {
                console.error("Failed to copy link:", error);
            }

            document.body.removeChild(textarea);
        }
    });
}

!(function (l) {
    "use strict";
    l("#sidebarToggle, #sidebarToggleTop").on("click", function (e) {
        l("body").toggleClass("sidebar-toggled"), l(".sidebar").toggleClass("toggled"), l(".sidebar").hasClass("toggled") && l(".sidebar .collapse").collapse("hide");
    }),
        l(window).resize(function () {
            l(window).width() < 768 && l(".sidebar .collapse").collapse("hide"),
                l(window).width() < 480 && !l(".sidebar").hasClass("toggled") && (l("body").addClass("sidebar-toggled"), l(".sidebar").addClass("toggled"), l(".sidebar .collapse").collapse("hide"));
        }),
        l("body.fixed-nav .sidebar").on("mousewheel DOMMouseScroll wheel", function (e) {
            var o;
            768 < l(window).width() && ((o = (o = e.originalEvent).wheelDelta || -o.detail), (this.scrollTop += 30 * (o < 0 ? 1 : -1)), e.preventDefault());
        }),
        l(document).on("scroll", function () {
            100 < l(this).scrollTop() ? l(".scroll-to-top").fadeIn() : l(".scroll-to-top").fadeOut();
        }),
        l(document).on("click", "a.scroll-to-top", function (e) {
            var o = l(this);
            l("html, body")
                .stop()
                .animate({ scrollTop: l(o.attr("href")).offset().top }, 1e3, "easeInOutExpo"),
                e.preventDefault();
        });
})(jQuery);
