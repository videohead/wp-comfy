<?php
/**
 * Plugin Name: ComfyUI Generate Button
 * Description: Adds a Generate button to WordPress posts that triggers FastAPI.
 */

add_action('post_submitbox_misc_actions', function() {
    global $post;

    if (!$post) return;

    ?>
    <div id="comfy-generate-box" style="padding:10px; border-top:1px solid #ddd;">
        <button id="comfy-generate-btn"
                class="button button-primary"
                style="width:100%; margin-top:10px;">
            Generate with ComfyUI
        </button>

        <div id="comfy-generate-status"
             style="margin-top:10px; font-weight:bold;"></div>

        <script>
            document.addEventListener("DOMContentLoaded", function() {
                const btn = document.getElementById("comfy-generate-btn");
                const status = document.getElementById("comfy-generate-status");

                btn.addEventListener("click", function() {
                    status.innerHTML = "Sending request to ComfyUI…";

                    fetch("http://10.0.0.34:8000/generate", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            post_id: <?php echo $post->ID; ?>
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.job_id) {
                            status.innerHTML =
                                "Job queued: " + data.job_id +
                                "<br>Check status at /status/" + data.job_id;
                        } else {
                            status.innerHTML = "Error: " + JSON.stringify(data);
                        }
                    })
                    .catch(err => {
                        status.innerHTML = "Request failed: " + err;
                    });
                });
            });
        </script>
    </div>
    <?php
});
