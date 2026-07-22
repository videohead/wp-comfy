<?php
/**
 * Plugin Name: ComfyUI Generate Button
 * Description: Adds a Generate button to WordPress posts that triggers FastAPI.
 * Version: 1.2.0
 * Author: Your Name
 */

// Plugin activation: set default settings
register_activation_hook(__FILE__, function() {
    if (!get_option('comfyui_api_url')) {
        add_option('comfyui_api_url', 'http://localhost:8183');
    }
});

// Add settings page
add_action('admin_menu', 'comfyui_add_settings_page');
function comfyui_add_settings_page() {
    add_options_page(
        'ComfyUI Settings',
        'ComfyUI',
        'manage_options',
        'comfyui-settings',
        'comfyui_render_settings_page'
    );
}

function comfyui_render_settings_page() {
    ?>
    <div class="wrap">
        <h1>ComfyUI Settings</h1>
        <form method="post" action="options.php">
            <?php settings_fields('comfyui_settings'); ?>
            <?php do_settings_sections('comfyui-settings'); ?>
            <table class="form-table">
                <tr>
                    <th scope="row">API URL</th>
                    <td>
                        <input type="text" name="comfyui_api_url"
                               value="<?php echo esc_attr(get_option('comfyui_api_url')); ?>"
                               class="regular-text" />
                        <p class="description">Enter your ComfyUI/FastAPI server URL.</p>
                    </td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

register_setting('comfyui_settings', 'comfyui_api_url');

// Add the Generate button as a meta box in the post editor
add_action('add_meta_boxes', 'comfyui_add_meta_box');
function comfyui_add_meta_box() {
    add_meta_box(
        'comfyui_generate',
        'ComfyUI Generate',
        'comfyui_render_meta_box',
        'post',
        'side',
        'high'
    );
}

function comfyui_render_meta_box($post) {
    wp_nonce_field('comfyui_generate_action', 'comfyui_nonce_field');
    ?>
    <div id="comfy-generate-box">
        <button id="comfy-generate-btn"
                class="button button-primary"
                style="width:100%; margin-top:5px;">
            Generate with ComfyUI
        </button>
        <div id="comfy-generate-status"
             style="margin-top:8px; font-size:13px; color:#444;"></div>
    </div>
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        var btn = document.getElementById("comfy-generate-btn");
        if (!btn) return;

        btn.addEventListener("click", function() {
            var status = document.getElementById("comfy-generate-status");
            status.innerHTML = "Sending request to ComfyUI\u2026";
            btn.disabled = true;

            fetch("<?php echo esc_url(admin_url('admin-ajax.php')); ?>", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: new URLSearchParams({
                    action: "comfyui_generate",
                    nonce: "<?php echo wp_create_nonce('comfyui_generate_nonce'); ?>",
                    post_id: <?php echo (int)$post->ID; ?>
                })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.success) {
                    status.innerHTML = "Job queued: " + data.data.job_id +
                        "<br>Check status at /status/" + data.data.job_id;
                } else {
                    status.innerHTML = "Error: " + (data.message || JSON.stringify(data));
                }
            })
            .catch(function(err) {
                status.innerHTML = "Request failed: " + err;
            })
            .finally(function() {
                btn.disabled = false;
            });
        });
    });
    </script>
    <?php
}

// Handle AJAX request
add_action('wp_ajax_comfyui_generate', 'comfyui_handle_generate');
function comfyui_handle_generate() {
    check_ajax_referer('comfyui_generate_nonce', 'nonce');

    $post_id = intval($_POST['post_id'] ?? 0);
    if (!$post_id) {
        wp_send_json_error(array('message' => 'Invalid post ID.'));
    }

    $api_url = get_option('comfyui_api_url', 'http://localhost:8183');
    $endpoint = rtrim($api_url, '/') . '/generate';

    $response = wp_remote_post($endpoint, array(
        'body'    => json_encode(array('post_id' => $post_id)),
        'headers' => array('Content-Type' => 'application/json'),
        'timeout' => 30,
    ));

    if (is_wp_error($response)) {
        wp_send_json_error(array('message' => $response->get_error_message()));
    }

    $body = wp_remote_retrieve_body($response);
    $data = json_decode($body, true);

    if (wp_remote_retrieve_response_code($response) >= 400) {
        wp_send_json_error(array('message' => 'API error: ' . ($data['message'] ?? 'Unknown error')));
    }

    wp_send_json_success($data);
}
