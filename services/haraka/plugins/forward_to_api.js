/**
 * Haraka plugin to forward received emails to FastAPI backend
 *
 * This plugin intercepts emails after they're received and forwards them
 * to the email-processor service via HTTP POST.
 */

const axios = require('axios');

exports.register = function() {
    this.loginfo('Forward to API plugin loaded');

    // Get configuration from environment
    this.cfg = {
        url: process.env.EMAIL_PROCESSOR_URL || 'http://email-processor:8000',
        api_key: process.env.API_KEY || 'dev-secret-key',
        timeout: 10000, // 10 seconds
    };

    this.loginfo(`Forwarding emails to: ${this.cfg.url}/webhook/email`);
};

exports.hook_queue = function(next, connection) {
    const plugin = this;
    const transaction = connection.transaction;

    if (!transaction) {
        plugin.logerror('No transaction found');
        return next(DENY, 'Transaction error');
    }

    // Extract email data
    const emailData = {
        message_id: transaction.header.get('message-id') || `<${transaction.uuid}@haraka>`,
        from: transaction.mail_from ? transaction.mail_from.address() : '',
        to: transaction.rcpt_to.map(rcpt => rcpt.address()),
        subject: transaction.header.get('subject') || '',
        headers: extractHeaders(transaction.header),
        text: transaction.body ? transaction.body.bodytext : '',
        html: extractHtmlBody(transaction),
        received_at: new Date().toISOString(),
    };

    // Log email reception
    plugin.loginfo(`Received email: ${emailData.message_id} from ${emailData.from} to ${emailData.to.join(', ')}`);

    // Forward to FastAPI
    axios.post(
        `${plugin.cfg.url}/webhook/email`,
        emailData,
        {
            timeout: plugin.cfg.timeout,
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': plugin.cfg.api_key,
            },
        }
    )
    .then(response => {
        plugin.loginfo(`Email forwarded successfully: ${emailData.message_id} (status: ${response.status})`);
        next(OK, `Email queued for processing`);
    })
    .catch(error => {
        plugin.logerror(`Failed to forward email: ${error.message}`);

        // Return temporary failure so sender can retry
        if (error.code === 'ECONNREFUSED' || error.code === 'ETIMEDOUT') {
            next(DENYSOFT, 'Temporary service unavailable, please retry');
        } else {
            // For other errors, accept email but log error
            // (we don't want to lose emails due to API issues)
            plugin.logerror(`Accepting email despite forwarding failure: ${emailData.message_id}`);
            next(OK, 'Email accepted');
        }
    });
};

/**
 * Extract headers as a clean object
 */
function extractHeaders(header) {
    const headers = {};
    const headerLines = header.headers_decoded || {};

    for (const [key, value] of Object.entries(headerLines)) {
        headers[key.toLowerCase()] = Array.isArray(value) ? value.join(', ') : value;
    }

    return headers;
}

/**
 * Extract HTML body if present
 */
function extractHtmlBody(transaction) {
    if (!transaction.body) return '';

    const body = transaction.body;

    // Check for HTML in multipart
    if (body.children && body.children.length > 0) {
        for (const child of body.children) {
            if (child.ct && child.ct.indexOf('text/html') !== -1) {
                return child.bodytext || '';
            }
        }
    }

    // Check main body content-type
    if (body.header && body.header.get('content-type') &&
        body.header.get('content-type').indexOf('text/html') !== -1) {
        return body.bodytext || '';
    }

    return '';
}
