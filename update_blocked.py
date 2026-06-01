import re

file_path = 'd:/LyraSixShare/LyraerpFinalProject/Lyraerp/templates/site_blocked.html'
with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Add endif for left section
search_str1 = """                <div class="icon-container">
                    <i class="bi bi-shield-lock"></i>
                </div>
            </div>"""
replace_str1 = """                <div class="icon-container">
                    <i class="bi bi-shield-lock"></i>
                </div>
                {% endif %}
            </div>"""
html = html.replace(search_str1, replace_str1)
html = html.replace(search_str1.replace('\n', '\r\n'), replace_str1.replace('\n', '\r\n'))

# Replace right section start
search_str2 = """            <div class="right-section">
                <div class="restriction-header">"""
replace_str2 = """            <div class="right-section">
                {% if restriction_type == 'permission' %}
                <div class="restriction-header">
                    <h2>Permission Denied</h2>
                    <p>Your access has been restricted</p>
                </div>

                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <div class="alert-content">
                        <strong>Missing Permissions</strong>
                        <p>You lack the necessary permissions to view the <strong>{{ blocked_module|default:"requested" }}</strong> module.</p>
                    </div>
                </div>

                <p class="info-text">
                    If you believe this is an error, please reach out to your system administrator to adjust your role access settings.
                </p>

                <a href="javascript:history.back()" class="commmombtn">
                    <i class="bi bi-arrow-left"></i>
                    <span>Go Back</span>
                </a>
                
                <a href="{% url 'logout' %}" class="commmombtn btn-logout">
                    <i class="bi bi-box-arrow-right"></i>
                    <span>Logout</span>
                </a>

                <div class="divider"></div>

                <p class="help-text">
                    Need help? Contact your system administrator or<br>
                    <a href="mailto:{{ contact_email|default:'lyraerp@techlyra.com' }}">{{ contact_email|default:'lyraerp@techlyra.com' }}</a>
                </p>
                {% else %}
                <div class="restriction-header">"""
html = html.replace(search_str2, replace_str2)
html = html.replace(search_str2.replace('\n', '\r\n'), replace_str2.replace('\n', '\r\n'))

# Add endif at the bottom
search_str3 = """                <p class="help-text">
                    Need help? Contact your system administrator or<br>
                    <a href="mailto:lyraerp@techlyra.com">lyraerp@techlyra.com</a>
                </p>
            </div>"""
replace_str3 = """                <p class="help-text">
                    Need help? Contact your system administrator or<br>
                    <a href="mailto:lyraerp@techlyra.com">lyraerp@techlyra.com</a>
                </p>
                {% endif %}
            </div>"""
html = html.replace(search_str3, replace_str3)
html = html.replace(search_str3.replace('\n', '\r\n'), replace_str3.replace('\n', '\r\n'))

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Done")
