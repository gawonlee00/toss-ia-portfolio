def number_to_korean_won(value: int) -> str:
    """정수 원화 금액을 '오천구백만 원' 형태로 읽는다."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 0
    n = max(n, 0)
    if n == 0:
        return "영 원"

    digits = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    small = ["", "십", "백", "천"]
    big = ["", "만", "억", "조", "경"]

    def chunk_to_korean(chunk: int) -> str:
        s = f"{chunk:04d}"
        out = []
        for i, ch in enumerate(s):
            d = int(ch)
            if d == 0:
                continue
            pos = 3 - i
            if d != 1 or pos == 0:
                out.append(digits[d])
            out.append(small[pos])
        return "".join(out)

    chunks = []
    group = 0
    while n > 0 and group < len(big):
        chunk = n % 10000
        if chunk:
            chunks.append((group, chunk))
        n //= 10000
        group += 1

    parts = []
    for group, chunk in reversed(chunks):
        parts.append(chunk_to_korean(chunk) + big[group])
    return "".join(parts) + " 원"
