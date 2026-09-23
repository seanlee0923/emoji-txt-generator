#!/usr/bin/env python3
"""
단색(또는 체크무늬) 배경을 진짜 투명(RGBA alpha=0)으로 바꿔주는 스크립트.

원리: 이미지 네 귀퉁이 색을 평균 내서 '배경색'으로 잡고, 가장자리부터 시작해
그 배경색과 색이 비슷한(색 거리가 가까운) 픽셀들만 이어서 투명 처리함(flood fill).
검은 테두리선처럼 배경색과 확실히 다른 색은 '벽'처럼 막아주기 때문에,
테두리 안쪽에 있는 흰 옷/눈동자 같은 부분은 배경과 이어져 있지 않으면 안 지워짐.

사용법: python remove_bg.py <입력이미지> -o <출력.png>
"""

import argparse
from collections import deque
from PIL import Image


def color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5


def sample_background_color(pixels, w, h):
    corners = [pixels[0, 0], pixels[w - 1, 0], pixels[0, h - 1], pixels[w - 1, h - 1]]
    corners = [c[:3] for c in corners]
    r = sum(c[0] for c in corners) / 4
    g = sum(c[1] for c in corners) / 4
    b = sum(c[2] for c in corners) / 4
    return (r, g, b)


def remove_background(path, tolerance=40):
    image = Image.open(path).convert("RGBA")
    w, h = image.size
    pixels = image.load()

    bg_color = sample_background_color(pixels, w, h)

    visited = bytearray(w * h)  # 0 = 안 봄, 1 = 배경으로 확정
    q = deque()

    def idx(x, y):
        return y * w + x

    def is_bg(x, y):
        r, g, b, a = pixels[x, y]
        return color_distance((r, g, b), bg_color) <= tolerance

    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y):
                i = idx(x, y)
                if not visited[i]:
                    visited[i] = 1
                    q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(x, y):
                i = idx(x, y)
                if not visited[i]:
                    visited[i] = 1
                    q.append((x, y))

    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                ni = idx(nx, ny)
                if not visited[ni]:
                    if is_bg(nx, ny):
                        visited[ni] = 1
                        q.append((nx, ny))
                    else:
                        visited[ni] = 2

    for y in range(h):
        for x in range(w):
            if visited[idx(x, y)] == 1:
                r, g, b, a = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)

    return image, bg_color


def main():
    parser = argparse.ArgumentParser(description="단색/체크무늬 배경을 진짜 투명으로 변환")
    parser.add_argument("image", help="입력 이미지 경로 (png, jpg 등)")
    parser.add_argument("-o", "--output", required=True, help="저장할 출력 PNG 경로")
    parser.add_argument("-t", "--tolerance", type=float, default=40,
                         help="배경색과의 색 거리 허용치 (기본값: 40). 배경이 덜 지워지면 값을 올리고, "
                              "캐릭터가 같이 지워지면 값을 내리세요")

    args = parser.parse_args()
    result, bg_color = remove_background(args.image, tolerance=args.tolerance)
    result.save(args.output)
    print(f"감지된 배경색: RGB({bg_color[0]:.0f}, {bg_color[1]:.0f}, {bg_color[2]:.0f})")
    print(f"저장 완료: {args.output}")


if __name__ == "__main__":
    main()
