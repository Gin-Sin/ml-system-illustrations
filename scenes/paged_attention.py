"""An original, geometry-first visual explanation of PagedAttention.

Render with scripts/render.py. No LaTeX installation is required.
Each chapter exports its own caption timings for the accessible web player.
"""
import json
from pathlib import Path

import numpy as np
from manim import *

BG = "#0b1018"
INK = "#edf1f7"
MUTED = "#92a0b5"
BLUE = "#69b7ff"
TEAL = "#63dec1"
GOLD = "#f1c77a"
PURPLE = "#bb9aff"
RED = "#f28d9b"
EDGE = "#354257"


def label(s, size=24, color=INK, **kwargs):
    return Text(str(s), font="DejaVu Sans", font_size=size, color=color, **kwargs)


def math(s, size=34, color=INK):
    return Text(s, font="DejaVu Serif", font_size=size, color=color)


def tile(s="", color=BLUE, width=0.75, height=0.63, fill=0.15):
    box = RoundedRectangle(width=width, height=height, corner_radius=0.09,
                           stroke_color=color, stroke_width=1.7,
                           fill_color=color, fill_opacity=fill)
    txt = label(s, 20, color).move_to(box)
    return VGroup(box, txt)


def page(tokens, color=BLUE, title=None, width=2.5):
    cells = VGroup(*[tile(t, color if t != "·" else EDGE, width=(width - .18) / 4,
                         height=.6) for t in tokens]).arrange(RIGHT, buff=.06)
    if title is None:
        return cells
    name = label(title, 17, color).next_to(cells, UP, buff=.16)
    return VGroup(cells, name)


class Chapter(Scene):
    number = "01"
    heading = ""

    def setup(self):
        self.camera.background_color = BG
        self.cues = []
        self.current_caption = None
        self.current_start = 0
        self.current_text = ""
        self.chrome = VGroup(
            label("ML SYSTEMS / VISUAL NOTES", 13, MUTED).to_corner(UL, buff=.45),
            label(f"{self.number} / 06", 14, TEAL).to_corner(UR, buff=.45),
            label("GIN-SIN", 12, MUTED).to_corner(DR, buff=.28),
            Line(LEFT * 6.6, RIGHT * 6.6, stroke_color=EDGE, stroke_width=1).shift(DOWN * 2.82),
        )
        self.add(self.chrome)
        self.title = label(self.heading, 35).move_to(UP * 2.95)
        self.play(Write(self.title), run_time=1)

    def caption(self, text):
        now = float(self.renderer.time)
        if self.current_text:
            self.cues.append({"start": self.current_start, "end": now, "text": self.current_text})
        self.current_start, self.current_text = now, text.replace("\n", " ")
        new = label(text, 21, INK, line_spacing=.7).move_to(DOWN * 3.25)
        if new.width > 12.4:
            new.scale_to_fit_width(12.4)
        if self.current_caption is None:
            self.play(FadeIn(new, shift=UP * .08), run_time=.35)
        else:
            self.play(ReplacementTransform(self.current_caption, new), run_time=.35)
        self.current_caption = new

    def finish(self):
        self.wait(1.5)
        self.cues.append({"start": self.current_start, "end": float(self.renderer.time),
                          "text": self.current_text})
        target = Path("media/timings")
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{self.__class__.__name__}.json").write_text(json.dumps({
            "title": self.heading, "duration": float(self.renderer.time), "cues": self.cues,
        }, indent=2))


class KVCache(Chapter):
    number, heading = "01", "Every new token carries a memory"

    def construct(self):
        self.caption("During decoding, each token contributes a key and a value to the KV cache.")
        words = ["The", "next", "great", "idea", "begins", "with"]
        tokens = VGroup(*[tile(w, BLUE, 1.28, .64) for w in words]).arrange(RIGHT, buff=.22).shift(UP * 1.48)
        keys = VGroup(*[tile(f"k{i}", TEAL, 1.28) for i in range(6)]).arrange(RIGHT, buff=.22).shift(UP * .35)
        vals = VGroup(*[tile(f"v{i}", PURPLE, 1.28) for i in range(6)]).arrange(RIGHT, buff=.22).shift(DOWN * .45)
        arrows = VGroup(*[Arrow(a.get_bottom(), b.get_top(), buff=.08, color=EDGE,
                              stroke_width=2, max_tip_length_to_length_ratio=.2) for a, b in zip(tokens, keys)])
        self.play(LaggedStart(*[FadeIn(t, shift=UP * .15) for t in tokens], lag_ratio=.14), run_time=1.8)
        self.play(LaggedStart(*[AnimationGroup(Create(arrows[i]), FadeIn(keys[i]), FadeIn(vals[i]))
                               for i in range(6)], lag_ratio=.15), run_time=2)
        self.wait(2)
        self.caption("The next query attends to the stored keys, then mixes the stored values.")
        eq = math("Attention(q, K, V) = softmax(qKᵀ / √d) V", 32).move_to(DOWN * 1.7)
        self.play(Write(eq), run_time=2)
        self.play(LaggedStart(*[Indicate(k, color=GOLD, scale_factor=1.09) for k in keys], lag_ratio=.13), run_time=2)
        self.wait(2)
        self.caption("As requests grow at different speeds, where should all these KV entries live?")
        brace = Brace(VGroup(keys, vals), RIGHT, color=GOLD)
        note = label("grows\nwith context", 18, GOLD).next_to(brace, RIGHT, buff=.12)
        self.play(GrowFromCenter(brace), FadeIn(note), run_time=1)
        self.wait(3)
        self.finish()


class Fragmentation(Chapter):
    number, heading = "02", "Reserving the future wastes the present"

    def construct(self):
        colors, lengths = [BLUE, TEAL, PURPLE], [6, 3, 5]
        self.caption("Imagine reserving 12 token slots per request, before its final length is known.")
        rows = VGroup()
        for i, (c, n) in enumerate(zip(colors, lengths)):
            cells = VGroup(*[tile(str(j) if j < n else "·", c if j < n else EDGE,
                                 .57, .53) for j in range(12)]).arrange(RIGHT, buff=.06)
            cells.move_to([.55, 1.45 - i * 1.05, 0])
            name = label(f"{chr(65+i)}  /  {n} tokens", 20, c).next_to(cells, LEFT, buff=.35)
            rows.add(VGroup(cells, name))
        self.play(LaggedStart(*[FadeIn(r) for r in rows], lag_ratio=.25), run_time=1.8)
        reserved = label("14 used  /  36 reserved", 25, GOLD).move_to(DOWN * 1.78)
        self.play(Write(reserved), run_time=1)
        self.wait(3)
        self.caption("Instead, allocate fixed-size blocks on demand. Here, one block holds four tokens.")
        groups = VGroup()
        for i, (c, n) in enumerate(zip(colors, lengths)):
            pgs = VGroup(*[page([str(j) if j < n else "·" for j in range(k, k+4)], c, width=2.38)
                           for k in range(0, n, 4)]).arrange(RIGHT, buff=.28)
            pgs.move_to([-.8, 1.45 - i * 1.05, 0]).align_to(rows[i][0], LEFT)
            groups.add(pgs)
        self.play(*[ReplacementTransform(rows[i][0], groups[i]) for i in range(3)],
                  FadeOut(reserved), run_time=2)
        efficient = label("14 used  /  20 allocated", 25, TEAL).move_to(DOWN * 1.78)
        self.play(Write(efficient), run_time=1)
        self.wait(2)
        self.caption("Only a request’s last block can have unused slots: at most B − 1 per sequence.")
        outlines = VGroup(*[SurroundingRectangle(g[-1], color=GOLD, buff=.08, corner_radius=.09) for g in groups])
        self.play(LaggedStart(*[Create(o) for o in outlines], lag_ratio=.2), run_time=1.2)
        self.wait(3)
        self.finish()


class BlockMapping(Chapter):
    number, heading = "03", "An address is a lookup, not a location"

    def construct(self):
        self.caption("Logical blocks preserve token order. Physical blocks can live anywhere in the pool.")
        logical = VGroup(*[page([str(j) if j < 10 else "·" for j in range(i*4, i*4+4)],
                                 BLUE, f"logical block {i}", 2.48) for i in range(3)]).arrange(DOWN, buff=.48).move_to([-4.5, .45, 0])
        table = VGroup(*[tile(f"{i}  →  {p}", GOLD, 1.55, .68) for i,p in enumerate([7,2,5])]).arrange(DOWN, buff=.5).move_to([-.8,.45,0])
        table_title = label("BLOCK TABLE", 16, GOLD).next_to(table, UP, buff=.35)
        physical = VGroup(*[tile(f"P{i}", EDGE, 1.2, .68) for i in range(8)]).arrange_in_grid(rows=4, cols=2, buff=(.25,.22)).move_to([3.85,.25,0])
        pool_title = label("GPU BLOCK POOL",16,MUTED).next_to(physical,UP,buff=.28)
        self.play(FadeIn(logical), FadeIn(table), FadeIn(table_title), FadeIn(physical), FadeIn(pool_title), run_time=1.5)
        for i,p in enumerate([7,2,5]):
            a = Arrow(table[i].get_right(), physical[p].get_left(), buff=.14, color=BLUE, stroke_width=2)
            self.play(Create(a), physical[p][0].animate.set_stroke(BLUE).set_fill(BLUE,opacity=.25),
                      physical[p][1].animate.set_color(BLUE), Indicate(logical[i],scale_factor=1.03),run_time=1)
        self.wait(2)
        self.caption("For token 6 with B = 4: logical block = floor(6 / 4) = 1, offset = 2.")
        eq=math("t = 6     →     b = 1,  r = 2     →     P2[2]",27,GOLD).move_to(DOWN*2.1)
        self.play(Write(eq),run_time=1.8)
        self.play(Indicate(logical[1][0][2],color=GOLD),Indicate(table[1],color=GOLD),run_time=1.4)
        self.wait(2)
        self.caption("The table maps logical block 1 to physical block 2. The token offset stays 2.")
        self.play(Indicate(physical[2],color=GOLD,scale_factor=1.12),run_time=1.4)
        self.wait(3)
        self.finish()


class Attention(Chapter):
    number, heading = "04", "Scattered storage. The same attention."

    def construct(self):
        self.caption("The attention kernel follows the block table to read the request’s keys and values.")
        q=tile("q",GOLD,1,1).move_to([-5.3,.7,0])
        blocks=VGroup(*[page([f"k{j}" for j in range(i*4,min(i*4+4,10))]+(["·","·"] if i==2 else []),
                                    c,f"P{p}  /  K, V",2.4) for i,(p,c) in enumerate(zip([7,2,5],[BLUE,TEAL,PURPLE]))]).arrange(RIGHT,buff=.65).move_to([.75,1.2,0])
        self.play(FadeIn(q),LaggedStart(*[FadeIn(b) for b in blocks],lag_ratio=.2),run_time=1.5)
        for b in blocks:
            a=CurvedArrow(q.get_top()+UP*.12,b.get_top()+UP*.2,angle=-.35,
                          color=GOLD,stroke_width=2,tip_length=.16)
            self.play(Create(a),Indicate(b,scale_factor=1.05),run_time=.8)
            self.play(FadeOut(a),run_time=.3)
        self.wait(1.5)
        self.caption("Each key produces a score. All valid scores share one softmax normalization.")
        score_rule = math("sᵢ = q · kᵢ / √d", 24, GOLD).move_to([.6, 2.15, 0])
        self.play(Write(score_rule), run_time=1)
        scores=VGroup(*[tile(f"s{i}",[BLUE,TEAL,PURPLE][i//4],.67,.55) for i in range(10)]).arrange(RIGHT,buff=.12).move_to([.3,-.25,0])
        self.play(LaggedStart(*[FadeIn(s,shift=DOWN*.25) for s in scores],lag_ratio=.08),run_time=1.7)
        brace=Brace(scores,DOWN,color=GOLD)
        norm=math("αᵢ = exp(sᵢ) / ∑ⱼ exp(sⱼ)",32,GOLD).next_to(brace,DOWN,buff=.2)
        self.play(GrowFromCenter(brace),Write(norm),run_time=1.6)
        self.wait(2.5)
        self.caption("Mix the values with these weights. Paging changes addresses, not the attention formula.")
        result=math("o = ∑ᵢ αᵢ vᵢ",34,TEAL).move_to(DOWN*2.22)
        self.play(Write(result),run_time=1.3)
        self.wait(3)
        self.finish()


class Allocation(Chapter):
    number, heading = "05", "Grow one block at a time"

    def construct(self):
        self.caption("A six-token request owns two blocks. Its last block still has room.")
        first=page(["0","1","2","3"],BLUE,"P7",2.65).move_to([-3.8,.7,0])
        tail=page(["4","5","·","·"],BLUE,"P2",2.65).move_to([-.4,.7,0])
        new=page(["·"]*4,EDGE,"P5 / free",2.65).move_to([3,.7,0])
        self.play(FadeIn(first),FadeIn(tail),FadeIn(new),run_time=1.3)
        count=label("6 tokens  /  2 allocated blocks",25,GOLD).move_to(DOWN*1)
        self.play(Write(count),run_time=.8)
        self.wait(2)
        self.caption("Tokens 6 and 7 fill existing space. No new physical block is needed.")
        for i in [6,7]:
            replacement=tile(str(i),BLUE,width=(2.65-.18)/4,height=.6).move_to(tail[0][i-4])
            self.play(Transform(tail[0][i-4],replacement),run_time=.8)
            self.wait(.7)
        c2=label("8 tokens  /  2 allocated blocks",25,GOLD).move_to(count)
        self.play(Transform(count,c2),run_time=.6)
        self.caption("Token 8 crosses a block boundary. Allocate a free block and extend the table.")
        allocated=page(["8","·","·","·"],BLUE,"P5",2.65).move_to(new)
        mapping=label("block table:  [7, 2]  →  [7, 2, 5]",24,TEAL).move_to(DOWN*1.75)
        self.play(Transform(new,allocated),Transform(count,label("9 tokens  /  3 allocated blocks",25,GOLD).move_to(count)),Write(mapping),run_time=1.5)
        self.wait(2.5)
        self.caption("When this request finishes, its unshared blocks return to the pool for reuse.")
        self.play(*[Transform(obj,page(["·"]*4,EDGE,f"P{p} / free",2.65).move_to(obj)) for obj,p in zip([first,tail,new],[7,2,5])],FadeOut(count),FadeOut(mapping),run_time=1.5)
        self.wait(2)
        self.finish()


class Sharing(Chapter):
    number, heading = "06", "Share the past. Copy only when writing."

    def construct(self):
        self.caption("Two continuations can share the same prefix blocks instead of duplicating their KV data.")
        a=tile("A: [7, 2]",BLUE,2.4,.7).move_to([-4.8,1.2,0])
        b=tile("B: [7, 2]",PURPLE,2.4,.7).move_to([-4.8,-.5,0])
        full=page(["0","1","2","3"],TEAL,"P7 / refs = 2",2.5).move_to([-.7,1.25,0])
        partial=page(["4","5","·","·"],GOLD,"P2 / refs = 2",2.5).move_to([3,1.25,0])
        arrows=VGroup(*[
            CurvedArrow(r.get_right()+RIGHT*.13,p[0].get_left()+LEFT*.13,
                        angle=-.35 if r is a else .4,color=c,stroke_width=1.8,tip_length=.16)
            if p is partial else Arrow(r.get_right(),p[0].get_left(),buff=.13,color=c,stroke_width=1.8)
            for r,c in [(a,BLUE),(b,PURPLE)] for p in [full,partial]])
        self.play(FadeIn(a),FadeIn(b),FadeIn(full),FadeIn(partial),run_time=1.2)
        self.play(LaggedStart(*[Create(x) for x in arrows],lag_ratio=.15),run_time=1.5)
        self.wait(2.5)
        self.caption("If A appends to a shared partial block, first copy that block to a new physical block.")
        copy=page(["4","5","·","·"],BLUE,"P5 / refs = 1",2.5).move_to([3,-.65,0])
        self.play(TransformFromCopy(partial,copy),run_time=1.7)
        self.play(Transform(a,tile("A: [7, 5]",BLUE,2.4,.7).move_to(a)),FadeOut(arrows[1]),
                  Transform(partial[1],label("P2 / refs = 1",17,GOLD).move_to(partial[1])),run_time=1)
        route=Arrow(a.get_right(),copy.get_left(),buff=.13,color=BLUE,stroke_width=1.8)
        self.play(Create(route),run_time=.6)
        self.caption("A writes token 6 into its private copy. B’s cache is untouched; the full prefix stays shared.")
        self.play(Transform(copy[0][2],tile("6",BLUE,width=(2.5-.18)/4,height=.6).move_to(copy[0][2])),run_time=.9)
        self.wait(3)
        recap=label("Less waste. More room for concurrent requests.",28,TEAL).move_to(DOWN*2.1)
        self.caption("PagedAttention combines block-based storage, address translation, and safe KV-cache sharing.")
        self.play(Write(recap),run_time=1.6)
        self.wait(3)
        self.finish()
