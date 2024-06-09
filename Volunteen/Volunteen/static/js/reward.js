$(document).ready(function() {
    $('.card-wrap').click(function() {
        var shopId = $(this).data('shop-id');
        $('.rewards-container').hide();
        $('#rewards-' + shopId).show();
    });
});
