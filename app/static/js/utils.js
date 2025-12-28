// UTC时间转换为本地时间（上海时区 UTC+8）
function convertUtcToShanghai() {
    $('.utc-time').each(function() {
        var $elem = $(this);
        var utcTimeStr = $elem.data('utc-time');
        if (utcTimeStr) {
            // 确保字符串以Z结尾（表示UTC时间）
            if (!utcTimeStr.endsWith('Z')) {
                utcTimeStr += 'Z';
            }
            // 创建UTC时间对象
            var utcDate = new Date(utcTimeStr);
            // 转换为上海时区（UTC+8）时间字符串（YYYY-MM-DD HH:MM格式）
            // 上海时区比UTC快8小时
            var shanghaiDate = new Date(utcDate.getTime() + (8 * 60 * 60 * 1000));
            var shanghaiTimeStr = shanghaiDate.getUTCFullYear() + '-' +
                String(shanghaiDate.getUTCMonth() + 1).padStart(2, '0') + '-' +
                String(shanghaiDate.getUTCDate()).padStart(2, '0') + ' ' +
                String(shanghaiDate.getUTCHours()).padStart(2, '0') + ':' +
                String(shanghaiDate.getUTCMinutes()).padStart(2, '0');
            $elem.text(shanghaiTimeStr);
        }
    });
}

// UTC时间转换为本地时间（浏览器本地时区）
function convertUtcToLocal() {
    $('.utc-time').each(function() {
        var $elem = $(this);
        var utcTimeStr = $elem.data('utc-time');
        if (utcTimeStr) {
            // 确保字符串以Z结尾（表示UTC时间）
            if (!utcTimeStr.endsWith('Z')) {
                utcTimeStr += 'Z';
            }
            // 创建UTC时间对象并转换为本地时间
            var utcDate = new Date(utcTimeStr);
            // 转换为本地时间字符串（YYYY-MM-DD HH:MM格式）
            var localTimeStr = utcDate.getFullYear() + '-' +
                String(utcDate.getMonth() + 1).padStart(2, '0') + '-' +
                String(utcDate.getDate()).padStart(2, '0') + ' ' +
                String(utcDate.getHours()).padStart(2, '0') + ':' +
                String(utcDate.getMinutes()).padStart(2, '0');
            $elem.text(localTimeStr);
        }
    });
}

// 初始化图片轮播 Modal
function initImageModal() {
    // Handle image modal show event
    $('#imageModal').on('show.bs.modal', function(event) {
        var button = $(event.relatedTarget); // Button that triggered the modal
        var imagesString = button.data('images'); // Extract image URLs from data attribute
        
        var modalBody = $(this).find('#imageModalBody');
        modalBody.empty(); // Clear previous content
        
        if (imagesString && imagesString.trim() !== '') {
            var images = imagesString.split(',').filter(function(img) {
                return img.trim() !== '';
            });
            
            if (images.length === 0) {
                modalBody.html('<p class="text-muted">暂无图片</p>');
            } else if (images.length === 1) {
                // Single image: show simple img tag
                modalBody.html('<img src="' + images[0].trim() + '" class="img-fluid" alt="故障图片">');
            } else {
                // Multiple images: show Bootstrap Carousel
                var carouselHtml = '<div id="imageCarousel" class="carousel slide" data-ride="carousel">';
                carouselHtml += '<ol class="carousel-indicators">';
                for (var i = 0; i < images.length; i++) {
                    carouselHtml += '<li data-target="#imageCarousel" data-slide-to="' + i + '"' + (i === 0 ? ' class="active"' : '') + '></li>';
                }
                carouselHtml += '</ol>';
                carouselHtml += '<div class="carousel-inner">';
                for (var i = 0; i < images.length; i++) {
                    carouselHtml += '<div class="carousel-item' + (i === 0 ? ' active' : '') + '">';
                    carouselHtml += '<img src="' + images[i].trim() + '" class="d-block w-100" alt="故障图片 ' + (i + 1) + '">';
                    carouselHtml += '</div>';
                }
                carouselHtml += '</div>';
                carouselHtml += '<a class="carousel-control-prev" href="#imageCarousel" role="button" data-slide="prev">';
                carouselHtml += '<span class="carousel-control-prev-icon" aria-hidden="true"></span>';
                carouselHtml += '<span class="carousel-control-text">上一张</span>';
                carouselHtml += '<span class="sr-only">上一张</span>';
                carouselHtml += '</a>';
                carouselHtml += '<a class="carousel-control-next" href="#imageCarousel" role="button" data-slide="next">';
                carouselHtml += '<span class="carousel-control-next-icon" aria-hidden="true"></span>';
                carouselHtml += '<span class="carousel-control-text">下一张</span>';
                carouselHtml += '<span class="sr-only">下一张</span>';
                carouselHtml += '</a>';
                carouselHtml += '</div>';
                modalBody.html(carouselHtml);
            }
        } else {
            modalBody.html('<p class="text-muted">暂无图片</p>');
        }
    });
    
    // Clear modal content when hidden
    $('#imageModal').on('hidden.bs.modal', function() {
        $(this).find('#imageModalBody').empty();
    });
}

// 页面加载完成后初始化
$(document).ready(function() {
    // Auto-convert UTC time to Shanghai timezone (for admin)
    // 注意：worker 端使用本地时间，需要在 worker base.html 中调用 convertUtcToLocal()
    convertUtcToShanghai();
    
    // Initialize image modal if it exists (mainly for worker pages)
    if ($('#imageModal').length > 0) {
        initImageModal();
    }
});

