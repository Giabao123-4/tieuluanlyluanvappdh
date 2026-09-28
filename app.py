from flask import Flask, render_template, request, redirect, url_for
import time
import re
import math
import difflib
import os
import json
import unicodedata
from urllib.parse import urlparse
from openai import OpenAI

app = Flask(__name__)


# ============================================================
# HỆ THỐNG MÔ PHỎNG LỪA ĐẢO TRỰC TUYẾN - PHỤC VỤ GIÁO DỤC
# ============================================================

SCENARIOS = {
    "1": {
        "title": "Cập nhật thông tin tài khoản Dịch vụ công Vneid",
        "icon": "vneid_icon_64.png",
        "color": "icon-red",
        "sender": "Cổng Dịch Vụ Công",
        "hook_message": "THÔNG BÁO KHẨN: Thông tin tài khoản của bạn chưa được xác minh. Bạn bắt buộc phải nhấn vào liên kết bên dưới để cập nhật VNeID ngay. Nếu không thực hiện, tài khoản có thể bị hạn chế sử dụng dịch vụ.",
        "fake_url_display": "http://dichvucong.bocongan-gov.vn/xac-minh",
        "form_title": "Cập nhật thông tin tài khoản",
        "template": "phishing_vneid.html",
        "inputs": [
            {
                "name": "Họ và tên",
                "type": "text",
                "pattern": r"^[a-zA-ZÀ-ỹ\s]+$",
                "msg": "Vui lòng nhập đúng họ và tên."
            },
            {
                "name": "Số CCCD",
                "type": "text",
                "pattern": r"^\d{12}$",
                "msg": "Vui lòng nhập đúng 12 số CCCD."
            },
            {
                "name": "Số điện thoại",
                "type": "text",
                "pattern": r"^0\d{9}$",
                "msg": "Vui lòng nhập số điện thoại 10 số."
            },
            {
                "name": "Mã OTP",
                "type": "text",
                "pattern": r"^\d{6}$",
                "msg": "Vui lòng nhập 6 số mã OTP."
            }
        ],
        "danger_step": "Cung cấp CCCD, Số điện thoại và đặc biệt là mã OTP cho một trang web lạ sẽ giúp kẻ gian chiếm đoạt tài khoản định danh và tài khoản ngân hàng.",
        "analysis_details": [
            {
                "title": "1. Yêu cầu thông tin bất thường",
                "content": "Cơ quan nhà nước KHÔNG BAO GIỜ yêu cầu cung cấp mã OTP qua một đường link được gửi từ tin nhắn."
            },
            {
                "title": "2. Tạo cảm giác cấp bách",
                "content": "Sử dụng lý do 'cần xác minh để tiếp tục sử dụng dịch vụ' khiến nạn nhân hoang mang và vội vàng làm theo."
            },
            {
                "title": "3. Tên miền giả mạo",
                "content": "Tên miền '.gov.vn' là duy nhất. Bất kỳ đuôi nào như '-gov.vn' hay '.gov.xyz' đều là lừa đảo."
            }
        ]
    },

    "2": {
        "title": "Nhận ngay quà tặng 500.000đ",
        "icon": "🎁",
        "color": "icon-purple",
        "sender": "Hệ thống Ưu đãi",
        "hook_message": "🎉 CHÚC MỪNG! Bạn đã được lựa chọn nhận phần quà trị giá 500.000đ! Phần quà đang chờ bạn xác nhận, hãy nhấn vào liên kết bên dưới để xác nhận thông tin và nhận quà ngay trước khi chương trình kết thúc.",
        "fake_url_display": "http://thuong-ngan-hang-2026.vn/nhan-thuong",
        "form_title": "Nhận Ngay Quà Tặng 500.000đ",
        "template": "phishing_bank.html",
        "inputs": [
            {
                "name": "Họ và tên",
                "type": "text",
                "pattern": r"^[a-zA-ZÀ-ỹ\s]+$",
                "msg": "Vui lòng nhập đúng họ và tên."
            },
            {
                "name": "Số tài khoản",
                "type": "text",
                "pattern": r"^\d{6,20}$",
                "msg": "Vui lòng nhập số tài khoản hợp lệ."
            },
            {
                "name": "Mã OTP",
                "type": "text",
                "pattern": r"^\d{6}$",
                "msg": "Vui lòng nhập 6 số mã OTP."
            }
        ],
        "danger_step": "Nhập mã OTP vào trang web nhận thưởng thực chất là bước phê duyệt cho kẻ gian chuyển tiền KHỎI tài khoản của bạn.",
        "analysis_details": [
            {
                "title": "1. Mồi nhử lòng tham",
                "content": "Các món quà giá trị cao bất ngờ là cách kẻ gian che mắt sự cảnh giác của người dùng."
            },
            {
                "title": "2. Sự vô lý của mã OTP",
                "content": "Nhận tiền KHÔNG CẦN mã OTP. Bạn chỉ dùng mã OTP khi tự mình chuyển tiền đi cho người khác."
            },
            {
                "title": "3. Xác minh qua kênh chính thức",
                "content": "Nên đăng nhập trực tiếp vào ứng dụng ngân hàng/ví điện tử để kiểm tra các thông báo ưu đãi."
            }
        ]
    },

    "3": {
        "title": "Cuộc gọi giả danh Công an",
        "icon": "👮",
        "color": "icon-blue",
        "sender": "09845569384",
        "video": "congan1.mp4",
        "audio": "congan1.mp3",
        "hook_message": "Chị đang liên quan đến một vụ án. Nếu không muốn bị điều tra hoặc quy tội, chị phải chuyển tiền để giải quyết vụ việc ngay. Nếu không thực hiện, hồ sơ sẽ được chuyển sang cơ quan điều tra. Xin cảm ơn!",
        "fake_url_display": "http://congan-xacminh-mophong.local/xu-ly",
        "form_title": "Cổng Xác Minh Hồ Sơ",
        "template": "scenario.html",
        "inputs": [
            {
                "name": "Họ và tên",
                "type": "text",
                "pattern": r"^[a-zA-ZÀ-ỹ\s]+$",
                "msg": "Nhập họ và tên đầy đủ."
            },
            {
                "name": "Số điện thoại",
                "type": "text",
                "pattern": r"^0\d{9}$",
                "msg": "Nhập số điện thoại 10 số."
            }

        ],
        "danger_step": "Cài đặt ứng dụng không rõ nguồn gốc sẽ làm điện thoại bị nhiễm mã độc chiếm quyền điều khiển.",
        "analysis_details": [
            {
                "title": "1. Giả danh cơ quan công quyền",
                "content": "Lợi dụng sự uy nghiêm của Công an để ép nạn nhân làm theo."
            },
            {
                "title": "2. Cài app độc hại",
                "content": "Không tải file .apk hoặc cấp quyền trợ năng cho ứng dụng lạ."
            }
        ]
    },

    "4": {
        "title": "Tuyển CTV Việc nhẹ lương cao",
        "icon": "💼",
        "color": "icon-green",
        "sender": "Hệ Thống Tuyển Dụng",
        "hook_message": "Công việc chốt đơn online, thời gian linh hoạt, có thể làm tại nhà. Thu nhập 400K - 800K/ngày. Đăng ký ngay!",
        "fake_url_display": "http://tuyendung-vieclam.vn/ung-tuyen",
        "form_title": "Tuyển CTV Việc nhẹ – Lương cao",
        "template": "phishing_job.html",
        "inputs": [
            {
                "name": "Họ và tên",
                "type": "text",
                "pattern": r"^[a-zA-ZÀ-ỹ\s]+$",
                "msg": "Vui lòng nhập họ và tên."
            },
            {
                "name": "Số điện thoại",
                "type": "text",
                "pattern": r"^0\d{9}$",
                "msg": "Vui lòng nhập đúng số điện thoại (10 số)."
            },
            {
                "name": "Địa chỉ",
                "type": "text",
                "pattern": r"^.+$",
                "msg": "Vui lòng nhập địa chỉ."
            },
            {
                "name": "Số tài khoản nhận lương",
                "type": "text",
                "pattern": r"^\d{6,20}$",
                "msg": "Vui lòng nhập số tài khoản."
            },
            {
                "name": "Mã xác thực",
                "type": "text",
                "pattern": r"^\d+$",
                "msg": "Vui lòng nhập mã xác thực."
            }
        ],
        "danger_step": "Cung cấp đầy đủ thông tin cá nhân và tài khoản cùng mã xác thực ngay từ bước đăng ký là dấu hiệu rõ ràng của việc lừa đảo thu thập dữ liệu hoặc chiếm đoạt tiền.",
        "analysis_details": [
            {
                "title": "1. Lời hứa hẹn phi lý",
                "content": "'Việc nhẹ, lương cao' thường là mồi nhử kinh điển nhất để đánh vào tâm lý người cần việc."
            },
            {
                "title": "2. Yêu cầu thông tin nhạy cảm",
                "content": "Đơn vị tuyển dụng chân chính không yêu cầu mã xác thực ngân hàng/SMS của bạn."
            },
            {
                "title": "3. Bẫy nạp tiền",
                "content": "Sau bước này, kẻ gian thường sẽ bắt nạn nhân chuyển khoản một khoản tiền cọc để nhận nhiệm vụ."
            }
        ]
    },

    "5": {
        "title": "Bạn quen nhờ chuyển tiền gấp",
        "icon": "💬",
        "color": "icon-blue",
        "sender": "Minh Anh",
        "hook_message": "Ê, tao đang có việc gấp. Điện thoại đang lỗi app ngân hàng chưa chuyển được. Mày chuyển giúp tao vào STK này nhé, lát app mở tao bank trả lại liền.",
        "fake_url_display": "http://xacnhan-chuyenkhoan-vnpay.com/ho-tro",
        "form_title": "Xác Nhận Chuyển Khoản",
        "template": "phishing_transfer.html",
        "inputs": [
            {
                "name": "Tên ngân hàng thụ hưởng",
                "type": "text",
                "pattern": r"^.+$",
                "msg": "Ví dụ: Vietcombank, Techcombank..."
            },
            {
                "name": "Số tài khoản người nhận",
                "type": "text",
                "pattern": r"^\d{6,20}$",
                "msg": "Nhập số tài khoản được cung cấp."
            },
            {
                "name": "Số tiền chuyển",
                "type": "number",
                "pattern": r"^\d+$",
                "msg": "Nhập đúng số tiền cần chuyển khoản."
            }
        ],
        "danger_step": "Chuyển tiền chỉ dựa vào tin nhắn mà không gọi điện xác thực trực tiếp.",
        "analysis_details": [
            {
                "title": "1. Mạo danh người thân",
                "content": "Kẻ gian dễ dàng giả mạo ảnh đại diện, tên, hoặc hack luôn tài khoản người quen của bạn."
            },
            {
                "title": "2. Quy tắc 2 bước",
                "content": "Luôn luôn gọi điện thoại bằng số điện thoại di động thông thường để xác nhận trước khi chuyển tiền."
            }
        ]
    },

    "6": {
        "title": "Chatbot thao túng tâm lý",
        "icon": "🤖",
        "color": "icon-purple",
        "sender": "Sự Kiện Tri Ân CSKH",
        "hook_message": "Bạn có tin nhắn mới.",
        "fake_url_display": "http://nhan-tien-thuong-2026.vn/xac-thuc",
        "form_title": "Cổng Xác Thực Nhận Tiền",
        "template": "phishing_chat.html",
        "inputs": [
            {
                "name": "Số tài khoản ngân hàng",
                "type": "text",
                "pattern": r"^\d{6,20}$",
                "msg": "Vui lòng nhập đúng số tài khoản."
            },
            {
                "name": "Mật khẩu App Ngân hàng",
                "type": "password",
                "pattern": r"^.+$",
                "msg": "Vui lòng nhập mật khẩu."
            },
            {
                "name": "Mã xác thực Smart OTP",
                "type": "text",
                "pattern": r"^\d{6,8}$",
                "msg": "Vui lòng nhập mã Smart OTP để nhận tiền."
            }
        ],
        "danger_step": "Cung cấp mật khẩu App Ngân hàng và mã Smart OTP cho một đường link lạ được gửi qua chat đồng nghĩa với việc giao toàn quyền kiểm soát tài khoản cho kẻ gian.",
        "analysis_details": [
            {
                "title": "1. Xây dựng lòng tin qua Chatbot",
                "content": "Kẻ gian sử dụng bot nhắn tin tự động với kịch bản được soạn sẵn để tạo cảm giác chuyên nghiệp và đáng tin cậy."
            },
            {
                "title": "2. Kéo dài cuộc hội thoại",
                "content": "Việc nhắn tin qua lại nhiều lần giúp hạ thấp sự phòng bị của nạn nhân trước khi tung ra đường link lừa đảo."
            },
            {
                "title": "3. Đánh cắp thông tin cốt lõi",
                "content": "Form giả mạo được thiết kế hệt như cổng đăng nhập ngân hàng, yêu cầu cả Mật khẩu và OTP để kẻ gian lập tức rút tiền."
            }
        ]
    }
}


# ============================================================
# CỖ MÁY PHÂN TÍCH URL
# ============================================================

def calculate_entropy(text):
    if not text:
        return 0

    entropy = 0

    for x in set(text):
        p_x = float(text.count(x)) / len(text)
        entropy += -p_x * math.log2(p_x)

    return entropy


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def remove_accents(input_str):
    """
    Loại bỏ dấu tiếng Việt để hỗ trợ phân tích chuỗi.
    """
    nfkd_form = unicodedata.normalize(
        "NFKD",
        input_str
    )

    return "".join(
        [
            c
            for c in nfkd_form
            if not unicodedata.combining(c)
        ]
    ).lower()


# ============================================================
# AI PHÂN TÍCH URL
# ============================================================

def analyze_url_with_ai(url, technical_details, score):
    """
    AI chỉ có nhiệm vụ giải thích các dấu hiệu kỹ thuật
    đã được hệ thống phát hiện.

    AI không thay thế bộ phân tích kỹ thuật.
    AI không được tự bịa kết quả từ các dịch vụ bên ngoài.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {
            "ai_status": "unavailable",
            "ai_verdict": "Chưa kết nối AI",
            "ai_confidence": 0,
            "ai_explanation": (
                "Hệ thống chưa được cấu hình OPENAI_API_KEY. "
                "Kết quả bên dưới vẫn dựa trên bộ phân tích "
                "URL kỹ thuật."
            ),
            "ai_risks": [],
            "ai_advice": [
                "Không nhập mật khẩu hoặc mã OTP vào URL chưa được xác minh.",
                "Kiểm tra website bằng cách truy cập trực tiếp trang chính thức.",
                "Không chuyển tiền khi chưa xác minh người nhận."
            ]
        }

    try:

        client = OpenAI(
            api_key=api_key
        )

        if technical_details:

            technical_text = "\n".join(
                f"- {item}"
                for item in technical_details
            )

        else:

            technical_text = (
                "- Chưa phát hiện dấu hiệu kỹ thuật rõ ràng."
            )

        prompt = f"""
Bạn là trợ lý AI hỗ trợ GIÁO DỤC AN TOÀN THÔNG TIN.

Nhiệm vụ của bạn là giải thích các dấu hiệu kỹ thuật
của một URL để giúp học sinh hiểu cách nhận diện
đường link đáng ngờ.

URL người dùng nhập:
{url}

Điểm rủi ro sơ bộ từ bộ phân tích kỹ thuật:
{score}/10

Các dấu hiệu kỹ thuật đã phát hiện:
{technical_text}

QUY TẮC:

1. Không được kết luận URL là lừa đảo chỉ vì xuất hiện
   một từ khóa như login, verify, bank, gift, payment...

2. Phải dựa trên nhiều đặc điểm:
   - Tên miền chính.
   - Subdomain.
   - Cấu trúc URL.
   - HTTP/HTTPS.
   - IP.
   - Punycode/Unicode.
   - Dấu @.
   - Port.
   - Typosquatting.
   - Giả mạo thương hiệu.
   - Các dấu hiệu kỹ thuật đã được cung cấp.

3. HTTPS KHÔNG có nghĩa website chắc chắn an toàn.

4. HTTP KHÔNG có nghĩa website chắc chắn là lừa đảo.

5. Nếu không đủ bằng chứng:
   phải nói rõ rằng chưa đủ bằng chứng để kết luận.

6. Không được bịa:
   - chủ sở hữu website
   - kết quả VirusTotal
   - kết quả Google
   - dữ liệu ngân hàng
   - dữ liệu người dùng
   - kết quả của dịch vụ bên ngoài

7. Chỉ giải thích những dấu hiệu có trong dữ liệu đầu vào.

8. Kết quả bằng TIẾNG VIỆT.

9. Giải thích đơn giản để học sinh hiểu:
   "Đường link đáng ngờ ở điểm nào?"

10. Không được coi danh sách từ khóa là bằng chứng duy nhất.

Trả về JSON đúng cấu trúc:

{{
    "verdict": "Rủi ro cao / Đáng ngờ / Chưa thấy dấu hiệu rõ ràng",
    "confidence": 0,
    "explanation": "Giải thích tổng quát bằng tiếng Việt.",
    "risks": [
        {{
            "title": "Tên tiêu chí",
            "detail": "Giải thích cụ thể."
        }}
    ],
    "advice": [
        "Khuyến cáo 1",
        "Khuyến cáo 2",
        "Khuyến cáo 3"
    ]
}}

confidence là số nguyên từ 0 đến 100.

Chỉ trả về JSON.
Không thêm Markdown.
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            tools=[
                {
                    "type": "web_search"
                }
            ],
            input=prompt
        )

        raw_text = response.output_text.strip()

        if raw_text.startswith("```"):

            raw_text = raw_text.replace(
                "```json",
                ""
            )

            raw_text = raw_text.replace(
                "```",
                ""
            )

            raw_text = raw_text.strip()

        ai_result = json.loads(
            raw_text
        )

        return {
            "ai_status": "success",

            "ai_verdict": ai_result.get(
                "verdict",
                "Chưa đủ dữ liệu để kết luận"
            ),

            "ai_confidence": ai_result.get(
                "confidence",
                0
            ),

            "ai_explanation": ai_result.get(
                "explanation",
                ""
            ),

            "ai_risks": ai_result.get(
                "risks",
                []
            ),

            "ai_advice": ai_result.get(
                "advice",
                []
            )
        }

    except Exception as e:

        print(
            "=========================================="
        )

        print(
            "AI ANALYSIS ERROR:"
        )

        print(e)

        print(
            "=========================================="
        )

        return {
            "ai_status": "error",

            "ai_verdict": (
                "Không thể phân tích bằng AI"
            ),

            "ai_confidence": 0,

            "ai_explanation": (
                "Hệ thống AI tạm thời không phản hồi. "
                "Kết quả kỹ thuật vẫn được giữ nguyên."
            ),

            "ai_risks": [],

            "ai_advice": [
                "Không nhập mật khẩu hoặc mã OTP.",
                "Kiểm tra tên miền trên website chính thức.",
                "Không chuyển tiền khi chưa xác minh."
            ]
        }


# ============================================================
# PHÂN TÍCH URL KỸ THUẬT
# ============================================================

def analyze_url_logic(url):

    original_url = (
        url or ""
    ).strip()

    if not original_url:
        return None

    # ========================================================
    # 1. CHUẨN HÓA URL
    # ========================================================

    if not original_url.lower().startswith(
        (
            "http://",
            "https://"
        )
    ):

        url_to_parse = (
            "http://" + original_url
        )

    else:

        url_to_parse = original_url

    try:

        parsed = urlparse(
            url_to_parse
        )

    except Exception:

        return None

    # ========================================================
    # 2. DOMAIN
    # ========================================================

    domain_full = (
        parsed.hostname or ""
    ).lower().strip(".")

    if not domain_full:

        return None

    domain_parts = (
        domain_full.split(".")
    )

    path_full = (
        parsed.path or ""
    )

    query_full = (
        parsed.query or ""
    )

    # ========================================================
    # 3. PROTOCOL
    # ========================================================

    protocol = (
        parsed.scheme.lower()
    )

    is_http = (
        protocol == "http"
    )

    is_https = (
        protocol == "https"
    )

    # ========================================================
    # 4. THÔNG TIN ĐẶC BIỆT
    # ========================================================

    try:

        port = parsed.port

    except ValueError:

        port = None

    has_username = (
        parsed.username is not None
    )

    has_password = (
        parsed.password is not None
    )

    # ========================================================
    # 5. XÁC ĐỊNH DOMAIN CHÍNH
    # ========================================================

    special_suffixes = [
        ("com", "vn"),
        ("net", "vn"),
        ("org", "vn"),
        ("edu", "vn"),
        ("gov", "vn"),
        ("ac", "vn")
    ]

    if (
        len(domain_parts) >= 3
        and tuple(domain_parts[-2:])
        in special_suffixes
    ):

        main_domain = ".".join(
            domain_parts[-3:]
        )

        subdomain = ".".join(
            domain_parts[:-3]
        )

    elif len(domain_parts) >= 2:

        main_domain = ".".join(
            domain_parts[-2:]
        )

        subdomain = ".".join(
            domain_parts[:-2]
        )

    else:

        main_domain = domain_full
        subdomain = ""

    # ========================================================
    # 6. DANH SÁCH DOMAIN CHÍNH THỨC
    # ========================================================

    official_domains = {
        "google.com",
        "facebook.com",
        "youtube.com",
        "apple.com",
        "microsoft.com",
        "github.com",
        "tiktok.com",
        "instagram.com",

        "vietcombank.com.vn",
        "techcombank.com.vn",
        "mbbank.com.vn",
        "bidv.com.vn",
        "agribank.com.vn",

        "vneid.gov.vn",
        "bocongan.gov.vn",
        "dichvucong.gov.vn",
        "chinhphu.vn",

        "shopee.vn",
        "lazada.vn",
        "tiki.vn",
        "momo.vn",
        "zalo.me"
    }

    is_official = (
        main_domain in official_domains
    )

    # ========================================================
    # 7. BIẾN KẾT QUẢ
    # ========================================================

    score = 0

    ai_details = []

    brand_detected = []

    typos_detected = []

    keywords_detected = []

    # ========================================================
    # 8. DOMAIN CHÍNH THỨC
    # ========================================================

    if is_official:

        ai_details.append(
            f"Tên miền chính '{main_domain}' "
            "nằm trong danh sách tên miền chính thức "
            "được hệ thống xác định."
        )

    # ========================================================
    # 9. @ / USERINFO
    # ========================================================

    if (
        has_username
        or has_password
        or "@" in original_url
    ):

        score += 7

        ai_details.append(
            "URL chứa thông tin người dùng hoặc ký tự '@'. "
            "Cấu trúc này có thể khiến người dùng hiểu nhầm "
            "đâu là tên miền thực sự."
        )

    # ========================================================
    # 10. HTTP
    # ========================================================

    if is_http:

        score += 2

        ai_details.append(
            "URL sử dụng HTTP thay vì HTTPS. "
            "HTTP không cung cấp lớp bảo vệ TLS như HTTPS. "
            "Đây là tín hiệu cần thận trọng nhưng không đủ "
            "để kết luận website là lừa đảo."
        )

    # ========================================================
    # 11. PORT
    # ========================================================

    if (
        port is not None
        and port not in [80, 443]
    ):

        score += 2

        ai_details.append(
            f"URL sử dụng cổng mạng không phổ biến "
            f"({port}). Cần kiểm tra thêm nguồn gốc "
            "của website."
        )

    # ========================================================
    # 12. URL QUÁ DÀI
    # ========================================================

    if len(original_url) > 150:

        score += 2

        ai_details.append(
            "URL có độ dài lớn bất thường. "
            "URL dài không đồng nghĩa với lừa đảo "
            "nhưng có thể làm người dùng khó nhận biết "
            "tên miền thật."
        )

    # ========================================================
    # 13. NHIỀU THAM SỐ
    # ========================================================

    if query_full:

        query_count = (
            query_full.count("&") + 1
        )

        if query_count >= 5:

            score += 2

            ai_details.append(
                "URL chứa nhiều tham số truy vấn. "
                "Cấu trúc phức tạp cần được kiểm tra thêm."
            )

    # ========================================================
    # 14. NHIỀU SUBDOMAIN
    # ========================================================

    if subdomain:

        sub_count = len(
            subdomain.split(".")
        )

        if sub_count >= 3:

            score += 3

            ai_details.append(
                "URL có nhiều tầng subdomain. "
                "Cấu trúc này có thể khiến người dùng "
                "nhầm subdomain với tên miền chính."
            )

    # ========================================================
    # 15. IP TRỰC TIẾP
    # ========================================================

    ipv4_pattern = (
        r"^(25[0-5]|2[0-4]\d|"
        r"1\d\d|[1-9]?\d)"
        r"(\.(25[0-5]|2[0-4]\d|"
        r"1\d\d|[1-9]?\d)){3}$"
    )

    if re.match(
        ipv4_pattern,
        domain_full
    ):

        score += 8

        ai_details.append(
            "URL sử dụng địa chỉ IP trực tiếp "
            "thay cho tên miền. Đây là dấu hiệu cần "
            "thận trọng đối với các liên kết yêu cầu "
            "đăng nhập hoặc cung cấp thông tin."
        )

    # ========================================================
    # 16. PUNYCODE
    # ========================================================

    if "xn--" in domain_full:

        score += 4

        ai_details.append(
            "Tên miền sử dụng Punycode (xn--). "
            "Cần kiểm tra kỹ vì một số tên miền quốc tế "
            "có thể tạo ra tên hiển thị dễ nhầm."
        )

    # ========================================================
    # 17. UNICODE
    # ========================================================

    try:

        unicode_chars = [
            c
            for c in domain_full
            if ord(c) > 127
        ]

        if (
            unicode_chars
            and "xn--" not in domain_full
        ):

            score += 4

            ai_details.append(
                "Tên miền chứa ký tự Unicode ngoài ASCII. "
                "Một số ký tự có thể nhìn tương tự "
                "chữ cái thông thường."
            )

    except Exception:
        pass

    # ========================================================
    # 18. GẠCH NGANG
    # ========================================================

    hyphen_count = (
        main_domain.count("-")
    )

    if hyphen_count >= 3:

        score += 2

        ai_details.append(
            "Tên miền chứa nhiều dấu gạch ngang. "
            "Đây là tín hiệu cần kiểm tra thêm về "
            "nguồn gốc và độ tin cậy của domain."
        )

    # ========================================================
    # 19. ENTROPY
    # ========================================================

    domain_name_only = (
        main_domain.split(".")[0]
    )

    if len(domain_name_only) >= 12:

        entropy = calculate_entropy(
            domain_name_only
        )

        if entropy >= 3.8:

            score += 3

            ai_details.append(
                "Phần tên miền có mức độ ngẫu nhiên "
                "tương đối cao. Đây là tín hiệu kỹ thuật "
                "cần kiểm tra thêm."
            )

    # ========================================================
    # 20. THƯƠNG HIỆU
    # ========================================================

    brands = {
        "vietcombank",
        "techcombank",
        "mbbank",
        "bidv",
        "agribank",
        "vneid",
        "bocongan",
        "dichvucong",
        "chinhphu",
        "shopee",
        "lazada",
        "tiki",
        "momo",
        "zalo",
        "facebook",
        "google",
        "apple",
        "microsoft"
    }

    domain_lower = (
        domain_full.lower()
    )

    for brand in brands:

        if brand in domain_lower:

            brand_detected.append(
                brand
            )

            # Domain chính thức thì không cộng điểm
            if main_domain in official_domains:

                continue

            score += 4

            ai_details.append(
                f"Tên miền có chứa tên thương hiệu "
                f"'{brand}' nhưng domain chính là "
                f"'{main_domain}', không trùng với "
                "domain chính thức đã biết."
            )

            break

    # ========================================================
    # 21. TYPOSQUATTING
    # ========================================================

    for brand in brands:

        similarity = similar(
            domain_name_only,
            brand
        )

        if (
            0.80 <= similarity < 1.0
            and domain_name_only != brand
            and len(domain_name_only) >= 5
        ):

            typos_detected.append(
                brand
            )

            score += 6

            ai_details.append(
                f"Tên miền '{domain_name_only}' "
                f"có mức độ tương đồng cao với "
                f"thương hiệu '{brand}'. Có thể là "
                "dấu hiệu giả mạo tên miền."
            )

            break

    # ========================================================
    # 22. GIẢ MẠO CƠ QUAN NHÀ NƯỚC
    # ========================================================

    government_brands = {
        "vneid",
        "bocongan",
        "dichvucong",
        "chinhphu"
    }

    for gov_brand in government_brands:

        if gov_brand in domain_lower:

            if not main_domain.endswith(
                ".gov.vn"
            ):

                score += 7

                ai_details.append(
                    f"Tên miền chứa '{gov_brand}' "
                    "nhưng không thuộc tên miền "
                    ".gov.vn tương ứng. Có dấu hiệu "
                    "cần kiểm tra khả năng giả mạo."
                )

            break

    # ========================================================
    # 23. URL ENCODED
    # ========================================================

    suspicious_encodings = [
        "%40",
        "%2f",
        "%2F",
        "%3A",
        "%3a",
        "%2e",
        "%2E"
    ]

    encoded_found = [
        value
        for value in suspicious_encodings
        if value in original_url
    ]

    if encoded_found:

        score += 2

        ai_details.append(
            "URL chứa các chuỗi mã hóa ký tự đặc biệt. "
            "Cần kiểm tra kỹ URL thực tế trước khi truy cập."
        )

    # ========================================================
    # 24. NHIỀU TẦNG DOMAIN
    # ========================================================

    if domain_full.count(".") >= 4:

        score += 2

        ai_details.append(
            "Tên miền có nhiều tầng phân cấp. "
            "Người dùng cần xác định chính xác "
            "domain chính trước khi đánh giá."
        )

    # ========================================================
    # 25. TỪ KHÓA - CHỈ THAM KHẢO
    # ========================================================

    educational_keywords = [
        "login",
        "verify",
        "account",
        "payment",
        "reward",
        "gift",
        "otp",
        "confirm",
        "update"
    ]

    normalized_url = remove_accents(
        original_url
    ).lower()

    for keyword in educational_keywords:

        if keyword in normalized_url:

            if keyword not in keywords_detected:

                keywords_detected.append(
                    keyword
                )

    # ========================================================
    # 26. GIỚI HẠN ĐIỂM
    # ========================================================

    score = min(
        max(
            math.ceil(score),
            0
        ),
        10
    )

    # ========================================================
    # 27. NẾU KHÔNG CÓ DẤU HIỆU
    # ========================================================

    if score == 0:

        ai_details.append(
            "Chưa phát hiện dấu hiệu kỹ thuật nổi bật "
            "trong các tiêu chí hiện có. Điều này không "
            "đồng nghĩa website chắc chắn an toàn."
        )

    # ========================================================
    # 28. TRẠNG THÁI
    # ========================================================

    if score >= 7:

        status_info = {
            "status": "danger",
            "text": "Rất nguy hiểm",
            "color": "#dc2626",
            "bg": "#fee2e2",
            "icon": "⚠️"
        }

    elif score >= 4:

        status_info = {
            "status": "warning",
            "text": "Đáng ngờ",
            "color": "#d97706",
            "bg": "#fef3c7",
            "icon": "⚡"
        }

    else:

        status_info = {
            "status": "safe",
            "text": "Chưa phát hiện dấu hiệu rõ ràng",
            "color": "#16a34a",
            "bg": "#dcfce7",
            "icon": "✓"
        }

    # ========================================================
    # 29. KẾT LUẬN KỸ THUẬT
    # ========================================================

    if score >= 7:

        verdict = (
            "URL có nhiều dấu hiệu kỹ thuật đáng ngờ. "
            "Không nên nhập thông tin cá nhân, mật khẩu, "
            "mã OTP hoặc thông tin tài chính."
        )

    elif score >= 4:

        verdict = (
            "URL có một số dấu hiệu cần thận trọng. "
            "Chưa nên cung cấp thông tin nhạy cảm trước "
            "khi xác minh website bằng nguồn chính thức."
        )

    else:

        verdict = (
            "Chưa phát hiện dấu hiệu kỹ thuật rõ ràng "
            "trong các tiêu chí hiện tại. Kết quả này "
            "không có nghĩa website được xác nhận an toàn."
        )

    # ========================================================
    # 30. AI PHÂN TÍCH
    # ========================================================

    ai_result = analyze_url_with_ai(
        original_url,
        ai_details,
        score
    )

    # ========================================================
    # 31. REPORT
    # ========================================================

    reports = [
        {
            "provider": "Phân tích cấu trúc URL",
            "type": "Phân tích kỹ thuật",
            "value": f"{len(ai_details)} dấu hiệu"
        },

        {
            "provider": "Tên miền",
            "type": "Domain",
            "value": main_domain
        },

        {
            "provider": "Subdomain",
            "type": "Domain",
            "value": (
                subdomain
                if subdomain
                else "Không có"
            )
        },

        {
            "provider": "Giao thức",
            "type": "Protocol",
            "value": protocol.upper()
        },

        {
            "provider": "Đánh giá tổng hợp",
            "type": "Mức rủi ro",
            "value": f"{score}/10"
        }
    ]

    # ========================================================
    # 32. TRẢ KẾT QUẢ
    # ========================================================

    return {

        "url": original_url,

        "score": score,

        "status_info": status_info,

        "main_domain": main_domain,

        "subdomain": subdomain,

        "is_official": is_official,

        "brand_detected": brand_detected,

        "typos_detected": typos_detected,

        "keywords_detected": keywords_detected,

        "ai_details": ai_details,

        "ai_analysis": ai_result,

        "reports": reports,

        "verdict": verdict
    }


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html",
        scenarios=SCENARIOS
    )


@app.route("/scenario/<id>")
def hook_stage(id):

    # Nếu là tình huống 6,
    # bay thẳng vào giao diện Chat

    if id == "6":

        return redirect(
            url_for(
                "phishing_stage",
                id=id
            )
        )

    data = SCENARIOS.get(
        id
    )

    if not data:

        return (
            "Không tìm thấy tình huống.",
            404
        )

    return render_template(
        "hook.html",
        data=data,
        id=id
    )


@app.route(
    "/phishing/<id>",
    methods=["GET", "POST"]
)
def phishing_stage(id):

    data = SCENARIOS.get(
        id
    )

    if not data:

        return (
            "Không tìm thấy tình huống.",
            404
        )

    if request.method == "POST":

        submitted = {}

        for index, field in enumerate(
            data.get(
                "inputs",
                []
            )
        ):

            key = f"field_{index}"

            value = request.form.get(
                key,
                ""
            ).strip()

            submitted[key] = value

        time.sleep(
            0.8
        )

        return render_template(
            "feedback_standalone.html",
            data=data,
            submitted=submitted,
            id=id
        )

    template_name = data.get(
        "template",
        "form.html"
    )

    return render_template(
        template_name,
        data=data,
        id=id
    )


# ============================================================
# URL ANALYZER
# ============================================================

@app.route(
    "/analyzer",
    methods=["GET", "POST"]
)
def url_analyzer():

    result = None
    url_input = ""

    if request.method == "POST":

        url_input = request.form.get(
            "url",
            ""
        ).strip()

        if url_input:

            time.sleep(
                0.5
            )

            result = analyze_url_logic(
                url_input
            )

    return render_template(
        "analyzer.html",
        result=result,
        url_input=url_input
    )


# ============================================================
# CHẠY ỨNG DỤNG
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )