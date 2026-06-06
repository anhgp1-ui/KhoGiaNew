import streamlit as st
import pandas as pd
import sqlite3
import os
import gdown

# ==========================
# CONFIG
# ==========================

st.set_page_config(
    page_title="Tra cứu kho giá V3",
    layout="wide"
)

DB_FILE = "kho_gia.db"

if not os.path.exists(DB_FILE):
    file_id = "14cyPLU-td2vvmm0Jkm6Hy01vDdHS_loB"
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, DB_FILE, quiet=False)

# ==========================
# SQLITE
# ==========================

@st.cache_resource
def get_conn():
    return sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )

conn = get_conn()

# ==========================
# HELPER
# ==========================

def format_money(df):

    df = df.copy()

    for col in ["Min", "Avg", "Max", "Giá duyệt"]:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

            df[col] = df[col].apply(
                lambda x:
                f"{x:,.0f}"
                if pd.notna(x)
                else ""
            )

    return df


def get_count(table_name):

    sql = f"""
    SELECT COUNT(*) AS total
    FROM {table_name}
    """

    return pd.read_sql_query(
        sql,
        conn
    )["total"][0]


def get_hang_xe_phutung():

    sql = """
    SELECT DISTINCT [Hãng xe]
    FROM phutung_master
    ORDER BY [Hãng xe]
    """

    return pd.read_sql_query(
        sql,
        conn
    )["Hãng xe"].tolist()


def get_hang_xe_son():

    sql = """
    SELECT DISTINCT [Hãng xe]
    FROM son_master
    ORDER BY [Hãng xe]
    """

    return pd.read_sql_query(
        sql,
        conn
    )["Hãng xe"].tolist()


def get_namsx():

    sql = """
    SELECT DISTINCT [Năm SX]
    FROM phutung_master
    ORDER BY [Năm SX]
    """

    df = pd.read_sql_query(
        sql,
        conn
    )

    return df["Năm SX"].tolist()


def get_tinh():

    sql = """
    SELECT DISTINCT [Tỉnh]
    FROM son_master
    ORDER BY [Tỉnh]
    """

    return pd.read_sql_query(
        sql,
        conn
    )["Tỉnh"].tolist()

# ==========================
# SIDEBAR
# ==========================

st.sidebar.title("📊 KHO GIÁ")

pt_master_count = get_count(
    "phutung_master"
)

pt_raw_count = get_count(
    "phutung_raw"
)

son_master_count = get_count(
    "son_master"
)

son_raw_count = get_count(
    "son_raw"
)

st.sidebar.info(
    f"""
🔧 PT Master: {pt_master_count:,}

📋 PT Raw: {pt_raw_count:,}

🎨 Sơn Master: {son_master_count:,}

📋 Sơn Raw: {son_raw_count:,}
"""
)

if st.sidebar.button(
    "🔄 Refresh Database"
):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

# ==========================
# HEADER
# ==========================

st.title(
    "🔍 TRA CỨU KHO GIÁ V3"
)

tab_pt, tab_son = st.tabs(
    [
        "🔧 Phụ tùng",
        "🎨 Sơn"
    ]
)

# =========================================
# TAB PHỤ TÙNG
# =========================================

with tab_pt:

    st.subheader("🔧 Tra cứu phụ tùng")

    # ------------------
    # Hãng xe
    # ------------------

    hang_xe = st.selectbox(
        "Hãng xe",
        [""] + get_hang_xe_phutung()
    )

    # ------------------
    # Dòng xe
    # ------------------

    dong_xe_options = []

    if hang_xe:

        sql = """
        SELECT DISTINCT [Dòng xe]
        FROM phutung_master
        WHERE [Hãng xe] = ?
        ORDER BY [Dòng xe]
        """

        dong_xe_raw = pd.read_sql_query(
            sql,
            conn,
            params=[hang_xe]
        )

        dong_xe_options = sorted(
            list(
                {
                    str(x).split()[0].upper()
                    for x in dong_xe_raw["Dòng xe"]
                    if pd.notna(x)
                }
            )
        )

    dong_xe_list = st.multiselect(
        "Dòng xe",
        dong_xe_options
    )

    # ------------------
    # Năm SX
    # ------------------

    nam_sx = st.selectbox(
        "Năm SX",
        [""] + [str(x) for x in get_namsx()]
    )

    # ------------------
    # Loại giá
    # ------------------

    loai_gia = st.selectbox(
        "Loại giá",
        [
            "",
            "Chính hãng",
            "Không chính hãng"
        ]
    )

    # ------------------
    # Tên phụ tùng
    # ------------------

    ten_pt = st.text_input(
        "Tên phụ tùng"
    )

    # ------------------
    # HSBT
    # ------------------

    show_history = st.checkbox(
        "Hiển thị lịch sử HSBT"
    )

    # =====================================
    # QUERY
    # =====================================

    sql = """
    SELECT
        [Tên phụ tùng],
        Min,
        Avg,
        Max,
        Count
    FROM phutung_master
    WHERE 1=1
    """

    params = []

    if hang_xe:

        sql += """
        AND [Hãng xe] = ?
        """

        params.append(
            hang_xe
        )

    if nam_sx:

        sql += """
        AND [Năm SX] = ?
        """

        params.append(
            int(nam_sx)
        )

    if loai_gia:

        sql += """
        AND [Loại giá] = ?
        """

        params.append(
            loai_gia
        )

    if ten_pt:

        sql += """
        AND [Tên phụ tùng]
        LIKE ?
        """

        params.append(
            f"%{ten_pt}%"
        )

    # =====================
    # MULTI DÒNG XE
    # =====================

    if dong_xe_list:

        like_clause = []

        for x in dong_xe_list:

            like_clause.append(
                "[Dòng xe] LIKE ?"
            )

            params.append(
                f"%{x}%"
            )

        sql += (
            " AND ("
            + " OR ".join(like_clause)
            + ")"
        )

    sql += """
    ORDER BY Count DESC
    """

    result = pd.read_sql_query(
        sql,
        conn,
        params=params
    )

    st.success(
        f"🔎 Tìm thấy {len(result):,} kết quả"
    )

    st.dataframe(
        format_money(result),
        hide_index=True,
        use_container_width=True,
        height=500
    )

    # =====================================
    # HSBT
    # =====================================

if show_history and ten_pt:

    st.divider()

    st.subheader("📋 Lịch sử HSBT")

    hist_sql = """
    SELECT
        [Số HSBT],
        [Ngày báo giá],
        [Hãng xe],
        [Dòng xe],
        [Năm SX],
        [Tên phụ tùng],
        [Giá duyệt]
    FROM phutung_raw
    WHERE 1=1
    """

    hist_params = []

    if hang_xe:
        hist_sql += " AND [Hãng xe] = ?"
        hist_params.append(hang_xe)

    if nam_sx:
        hist_sql += " AND [Năm SX] = ?"
        hist_params.append(int(nam_sx))

    if loai_gia:
        hist_sql += " AND [Loại giá] = ?"
        hist_params.append(loai_gia)

    if ten_pt:
        hist_sql += " AND [Tên phụ tùng] LIKE ?"
        hist_params.append(f"%{ten_pt}%")

    if dong_xe_list:

        like_clause = []

        for x in dong_xe_list:
            like_clause.append("[Dòng xe] LIKE ?")
            hist_params.append(f"%{x}%")

        hist_sql += (
            " AND ("
            + " OR ".join(like_clause)
            + ")"
        )

    hist_sql += """
    ORDER BY [Giá duyệt] DESC
    LIMIT 100
    """

    hist = pd.read_sql_query(
        hist_sql,
        conn,
        params=hist_params
    )

    st.dataframe(
        format_money(hist),
        hide_index=True,
        use_container_width=True,
        height=350
    )
# =========================================
# TAB SƠN
# =========================================

with tab_son:

    st.subheader("🎨 Tra cứu sơn")

    # ------------------
    # Hãng xe
    # ------------------

    hang_xe_son = st.selectbox(
        "Hãng xe",
        [""] + get_hang_xe_son(),
        key="son_hang_xe"
    )

    # ------------------
    # Dòng xe
    # ------------------

    dong_xe_options_son = []

    if hang_xe_son:

        sql = """
        SELECT DISTINCT [Dòng xe]
        FROM son_master
        WHERE [Hãng xe] = ?
        ORDER BY [Dòng xe]
        """

        dong_xe_raw_son = pd.read_sql_query(
            sql,
            conn,
            params=[hang_xe_son]
        )

        dong_xe_options_son = sorted(
            list(
                {
                    str(x).split()[0].upper()
                    for x in dong_xe_raw_son["Dòng xe"]
                    if pd.notna(x)
                }
            )
        )

    dong_xe_list_son = st.multiselect(
        "Dòng xe",
        dong_xe_options_son,
        key="son_dong_xe"
    )

    # ------------------
    # Tỉnh
    # ------------------

    tinh = st.selectbox(
        "Tỉnh",
        [""] + get_tinh(),
        key="son_tinh"
    )

    # ------------------
    # Loại giá
    # ------------------

    loai_gia_son = st.selectbox(
        "Loại giá",
        [
            "",
            "Chính hãng",
            "Không chính hãng"
        ],
        key="son_loai_gia"
    )

    # ------------------
    # Hạng mục
    # ------------------

    hang_muc = st.text_input(
        "Hạng mục",
        key="son_hang_muc"
    )

    # ------------------
    # HSBT
    # ------------------

    show_history_son = st.checkbox(
        "Hiển thị lịch sử HSBT",
        key="show_history_son"
    )

    # =====================================
    # QUERY MASTER
    # =====================================

    sql = """
    SELECT
        [Hạng mục],
        Min,
        Avg,
        Max,
        Count
    FROM son_master
    WHERE 1=1
    """

    params = []

    if hang_xe_son:

        sql += """
        AND [Hãng xe] = ?
        """

        params.append(
            hang_xe_son
        )

    if tinh:

        sql += """
        AND [Tỉnh] = ?
        """

        params.append(
            tinh
        )

    if loai_gia_son:

        sql += """
        AND [Loại giá] = ?
        """

        params.append(
            loai_gia_son
        )

    if hang_muc:

        sql += """
        AND [Hạng mục] LIKE ?
        """

        params.append(
            f"%{hang_muc}%"
        )

    if dong_xe_list_son:

        like_clause = []

        for x in dong_xe_list_son:

            like_clause.append(
                "[Dòng xe] LIKE ?"
            )

            params.append(
                f"%{x}%"
            )

        sql += (
            " AND ("
            + " OR ".join(like_clause)
            + ")"
        )

    sql += """
    ORDER BY Count DESC
    """

    result = pd.read_sql_query(
        sql,
        conn,
        params=params
    )

    st.success(
        f"🔎 Tìm thấy {len(result):,} kết quả"
    )

    st.dataframe(
        format_money(result),
        hide_index=True,
        use_container_width=True,
        height=500
    )

    # =====================================
    # LỊCH SỬ HSBT
    # =====================================

    if show_history_son and hang_muc:

        st.divider()

        st.subheader(
            "📋 Lịch sử HSBT"
        )

        # KHỞI TẠO TRƯỚC
        hist_sql = """
        SELECT
            [Số HSBT],
            [Ngày báo giá],
            [Hãng xe],
            [Dòng xe],
            [Hạng mục],
            [Giá duyệt]
        FROM son_raw
        WHERE 1=1
        """

        hist_params = []

        if hang_xe_son:

            hist_sql += """
            AND [Hãng xe] = ?
            """

            hist_params.append(
                hang_xe_son
            )

        if tinh:

            hist_sql += """
            AND [Tỉnh] = ?
            """

            hist_params.append(
                tinh
            )

        if loai_gia_son:

            hist_sql += """
            AND [Loại giá] = ?
            """

            hist_params.append(
                loai_gia_son
            )

        if hang_muc:

            hist_sql += """
            AND [Hạng mục] LIKE ?
            """

            hist_params.append(
                f"%{hang_muc}%"
            )

        if dong_xe_list_son:

            like_clause = []

            for x in dong_xe_list_son:

                like_clause.append(
                    "[Dòng xe] LIKE ?"
                )

                hist_params.append(
                    f"%{x}%"
                )

            hist_sql += (
                " AND ("
                + " OR ".join(like_clause)
                + ")"
            )

        hist_sql += """
        ORDER BY [Giá duyệt] DESC
        LIMIT 100
        """

        hist = pd.read_sql_query(
            hist_sql,
            conn,
            params=hist_params
        )

        st.dataframe(
            format_money(hist),
            hide_index=True,
            use_container_width=True,
            height=350
        )