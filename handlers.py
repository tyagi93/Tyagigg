import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

def format_vehicle_report(data: dict) -> str:
    return (
        "📋 Vehicle Information Report\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Owner: {data.get('owner', data.get('Owner', 'N/A'))}\n"
        f"👨‍👦 Father Name: {data.get('father_name', data.get('FatherName', 'NA'))}\n"
        f"🔢 Reg No: {data.get('reg_no', data.get('RegNo', 'N/A'))}\n"
        f"📅 Reg Date: {data.get('reg_date', data.get('RegDate', 'N/A'))}\n"
        f"🚘 Class: {data.get('class', data.get('Class', 'N/A'))}\n"
        f"⚙️ Vehicle Type: {data.get('vehicle_type', data.get('VehicleType', 'N/A'))}\n"
        f"🏭 Manufacturer: {data.get('manufacturer', data.get('Manufacturer', 'N/A'))}\n"
        f"📅 Mfg Month/Year: {data.get('mfg_date', data.get('MfgDate', 'N/A'))}\n"
        f"⛽ Fuel Type: {data.get('fuel_type', data.get('FuelType', 'N/A'))}\n"
        f"🎛️ Cubic Capacity: {data.get('cc', data.get('CubicCapacity', 'N/A'))}\n"
        f"💺 Seat Capacity: {data.get('seats', data.get('SeatCapacity', 'N/A'))}\n"
        f"🛠️ Engine No: {data.get('engine_no', data.get('EngineNo', 'N/A'))}\n"
        f"⛓️ Chassis No: {data.get('chassis_no', data.get('ChassisNo', 'N/A'))}\n"
        f"🏢 Authority: {data.get('authority', data.get('Authority', 'N/A'))}\n"
        f"📍 RTO: {data.get('rto', data.get('Rto', 'N/A'))}\n"
        f"🗺️ State: {data.get('state', data.get('State', 'N/A'))}\n"
        f"📮 Pincode: {data.get('pincode', data.get('Pincode', 'N/A'))}\n"
        f"🏡 Permanent Address: {data.get('address', data.get('Address', 'N/A'))}\n"
        f"💰 Financer: {data.get('financer', data.get('Financer', 'N/A'))}\n"
        f"💼 Commercial: {data.get('commercial', data.get('Commercial', 'N/A'))}\n"
        f"🛡️ Insurance Company: {data.get('insurance_company', data.get('InsuranceCompany', 'N/A'))}\n"
        f"🧾 Insurance Policy: {data.get('insurance_policy', data.get('InsurancePolicy', 'N/A'))}\n"
        f"📆 Insurance Upto: {data.get('insurance_upto', data.get('InsuranceUpto', 'N/A'))}\n"
        f"⚠️ Insurance Expired: {data.get('insurance_expired', data.get('InsuranceExpired', 'N/A'))}\n"
        f"💚 PUCC Valid Upto: {data.get('pucc_upto', data.get('PuccUpto', 'N/A'))}\n"
        f"🆔 API Database ID: {data.get('db_id', data.get('DatabaseId', 'N/A'))}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👑 Admin: @TYAGI8\n"
        "🤖 Bot: @TYAGI_NUMBER_INFO_BOT"
    )

def format_mobile_report(data: dict) -> str:
    return (
        "📋 Mobile Information Report\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📱 Number: {data.get('phone', data.get('mobile_no', 'N/A'))}\n"
        f"👤 Name: {data.get('name', 'N/A')}\n"
        f"📍 Circle: {data.get('circle', 'N/A')}\n"
        f"📡 Operator: {data.get('operator', 'N/A')}\n"
        f"🗺️ State: {data.get('state', 'N/A')}\n"
        f"🏠 Address: {data.get('address', 'N/A')}\n"
        f"🆔 API Database ID: {data.get('db_id', 'N/A')}\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "👑 Admin: @TYAGI8\n"
        "🤖 Bot: @TYAGI_NUMBER_INFO_BOT"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🚘 Vehicle Info", callback_data="menu_vehicle"),
            InlineKeyboardButton("📱 Number Info", callback_data="menu_mobile")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "👋 Welcome to Info Bot!\n\n"
        "Neeche diye gaye buttons mein se choose karein ki aapko kiski jankari chahiye:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_vehicle":
        context.user_data['mode'] = 'vehicle'
        await query.edit_message_text(
            text="🚘 **Vehicle Mode Selected**\n\nAap apna vehicle number bhejein (jaise: `UK04AQ9000`):",
            parse_mode="Markdown"
        )
    elif query.data == "menu_mobile":
        context.user_data['mode'] = 'mobile'
        await query.edit_message_text(
            text="📱 **Number Info Mode Selected**\n\nAap 10 digit ka mobile number bhejein:",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')
    
    if not mode:
        if text.isdigit() and len(text) == 10:
            mode = 'mobile'
        else:
            mode = 'vehicle'

    if mode == 'mobile':
        if not (text.isdigit() and len(text) == 10):
            await update.message.reply_text("❌ Kripya sahi 10 digit ka mobile number enter karein.")
            return
            
        await update.message.reply_text("🔍 Fetching mobile details...")
        try:
            api_url = f"https://rack-numinfo.vercel.app/api/lookup?phone={text}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                actual_data = data.get("data", data) if isinstance(data, dict) else data
                report = format_mobile_report(actual_data)
                await update.message.reply_text(report)
            else:
                await update.message.reply_text("❌ Mobile data not found or API error.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
            
    elif mode == 'vehicle':
        await update.message.reply_text("🔍 Fetching vehicle details...")
        try:
            v_no = text.replace(" ", "").upper()
            api_url = f"https://vehicleinfo-byrack.vercel.app/api?search={v_no}"
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                actual_data = data.get("data", data) if isinstance(data, dict) else data
                report = format_vehicle_report(actual_data)
                await update.message.reply_text(report)
            else:
                await update.message.reply_text("❌ Vehicle not found or API error.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")
            
