"""PagedAttention: geometric transformations, real LaTeX, and distinct type roles.

CMU Serif: narrative. JetBrains Mono: code/addresses. Computer Modern: MathTex.
Reference frames: 3blue1brown.com/lessons/attention. All scenes are original.
"""
import json
from html import escape
from pathlib import Path

import numpy as np
from manim import *

BG = "#000000"
INK = "#F5F3EF"
MUTED = "#AAA7A0"
BLUE = "#58C4DD"
TEAL = "#5CD0B3"
GOLD = "#FFFF80"
PURPLE = "#C792EA"
RED = "#FC6255"
EDGE = "#454545"
NARRATIVE_FONT = "CMU Serif"
CODE_FONT = "JetBrains Mono"
TEX_TEMPLATE = TexTemplate()
TEX_TEMPLATE.add_to_preamble(r"\usepackage{xcolor}")


def prose(text, size=30, color=INK, **kwargs):
    return Text(str(text), font=NARRATIVE_FONT, font_size=size, color=color, **kwargs)


def code(text, size=23, color=INK, **kwargs):
    return MarkupText(f'<span font_features="liga=0,calt=0">{escape(str(text))}</span>',
                      font=CODE_FONT, font_size=size, color=color, **kwargs)


def formula(*tex, size=42, color=INK, **kwargs):
    result = MathTex(*tex, font_size=size, tex_template=TEX_TEMPLATE, **kwargs)
    if not any(r"\textcolor" in part for part in tex):
        result.set_color(color)
    return result


def colored_glyphs(mobject, color):
    return VGroup(*[part for part in mobject.family_members_with_points()
                    if str(part.get_color()).upper() == color.upper()])


def arrow(start, end, color=INK, width=2, **kwargs):
    return Arrow(start, end, buff=.1, color=color, stroke_width=width,
                 max_tip_length_to_length_ratio=.14, tip_length=.13, **kwargs)


def column_vector(symbol, index, color, height=1.7):
    return formula(
        rf"\begin{{bmatrix}} {symbol}_{{{index},1}} \\ {symbol}_{{{index},2}} \\ \vdots \\ {symbol}_{{{index},d}} \end{{bmatrix}}",
        size=29, color=color,
    ).scale_to_fit_height(height)


class MemoryBlock(VGroup):
    """A continuous memory strip with dividers, not a row of UI cards."""
    def __init__(self, tokens, color=BLUE, width=2.6, height=.56, address=None, **kwargs):
        super().__init__(**kwargs)
        self.tint = color
        self.cells, self.labels, self.contents = VGroup(), VGroup(), VGroup()
        for i, token in enumerate(tokens):
            center = np.array([(i-(len(tokens)-1)/2)*width/len(tokens), 0, 0])
            rect = Rectangle(width=width/len(tokens), height=height,
                             stroke_width=.75, stroke_color=color if token is not None else EDGE,
                             fill_color=color, fill_opacity=.13 if token is not None else 0).move_to(center)
            mark = code(str(token), 19, color) if token is not None else VectorizedPoint(center)
            mark.move_to(center)
            self.cells.add(rect)
            self.labels.add(mark)
            self.contents.add(VGroup(rect, mark))
        self.outline = Rectangle(width=width, height=height, stroke_width=1.7,
                                 stroke_color=color, fill_opacity=0)
        self.add(self.contents, self.outline)
        self.address = code(address, 17, color).next_to(self.outline, UP, buff=.14) if address else VectorizedPoint()
        if address:
            self.add(self.address)

    def put(self, index, value, color=None):
        tint = color or self.tint
        return VGroup(
            self.cells[index].copy().set_stroke(tint, .75).set_fill(tint, .13),
            code(str(value), 19, tint).move_to(self.cells[index]),
        )


class Chapter(Scene):
    number = "01"
    heading = ""

    def setup(self):
        self.camera.background_color = BG
        self.cues = []
        self.current_caption = None
        self.current_text = ""
        self.current_start = 0
        self.reference_frames = []
        self.brand = prose("PagedAttention", 15, MUTED).to_corner(UL, buff=.23)
        self.chapter_number = prose(f"{self.number} / 06", 15, MUTED).to_corner(UR, buff=.23)
        self.add(self.brand, self.chapter_number)
        self.title = prose(self.heading, 38).move_to(UP*2.98)
        if self.title.width > 12.6:
            self.title.scale_to_fit_width(12.6)
        self.play(FadeIn(self.title, shift=UP*.12), run_time=1)

    def caption(self, text):
        now = float(self.renderer.time)
        if self.current_text:
            self.cues.append({"start":self.current_start, "end":now, "text":self.current_text})
        self.current_start, self.current_text = now, text
        wrapped = text
        if len(text) > 88:
            split = min((i for i,ch in enumerate(text) if ch == " "),
                        key=lambda i: abs(i-len(text)/2))
            wrapped = text[:split] + "\n" + text[split+1:]
        new = prose(wrapped, 23, "#D1CEC8", line_spacing=.8).move_to(DOWN*3.5)
        if new.width > 12.6:
            new.scale_to_fit_width(12.6)
        if self.current_caption is None:
            self.play(FadeIn(new), run_time=.35)
        else:
            self.play(FadeOut(self.current_caption), FadeIn(new), run_time=.35)
        self.current_caption = new

    def mark(self, name):
        self.reference_frames.append({"name":name,"time":float(self.renderer.time)})

    def finish(self):
        self.wait(2)
        self.cues.append({"start":self.current_start,"end":float(self.renderer.time),"text":self.current_text})
        target = Path("media/timings")
        target.mkdir(parents=True, exist_ok=True)
        (target/f"{self.__class__.__name__}.json").write_text(json.dumps({
            "title":self.heading,"duration":float(self.renderer.time),
            "cues":self.cues,"review_frames":self.reference_frames,
        }, indent=2))


class KVCache(Chapter):
    number, heading = "01", "What does the model remember?"

    def construct(self):
        self.caption("Each token leaves behind two vectors: a key and a value. One attention head is shown here.")
        words = VGroup(*[prose(w, 35) for w in ["A", "small", "idea", "grows"]])
        positions = [-4.65, -1.55, 1.55, 4.65]
        keys, values, stems = VGroup(), VGroup(), VGroup()
        for i, x in enumerate(positions):
            words[i].move_to([x, 1.85, 0])
            keys.add(column_vector("k", i, BLUE).move_to([x-.45, .35, 0]))
            values.add(column_vector("v", i, TEAL).move_to([x+.45, .35, 0]))
            stems.add(arrow(words[i].get_bottom(), [x, 1.3, 0], INK))
        self.play(LaggedStart(*[FadeIn(w,shift=UP*.2) for w in words[:3]],lag_ratio=.3),run_time=1.8)
        self.play(LaggedStart(*[AnimationGroup(GrowArrow(stems[i]),Write(keys[i]),Write(values[i]))
                               for i in range(3)],lag_ratio=.2),run_time=2.5)
        klabel = prose("keys", 27, BLUE).move_to([-1.8,-1,0])
        vlabel = prose("values", 27, TEAL).move_to([1.8,-1,0])
        self.play(FadeIn(klabel),FadeIn(vlabel),run_time=.6)
        self.wait(2.5)
        self.caption("Decoding appends another key–value pair. The earlier vectors stay in the cache.")
        self.play(FadeIn(words[3]),GrowArrow(stems[3]),Write(keys[3]),Write(values[3]),run_time=2)
        cache_brace = Brace(VGroup(keys,values),DOWN,color=INK,buff=.35)
        cache_label = prose("the KV cache", 32).next_to(cache_brace,DOWN,buff=.12)
        self.play(FadeOut(klabel),FadeOut(vlabel),GrowFromCenter(cache_brace),Write(cache_label),run_time=1.5)
        self.mark("kv-vectors")
        self.wait(3)
        self.caption("The next query reuses this growing cache to compute attention over the available context.")
        equation = formula(
            r"\mathbf{o}_t = \textcolor[HTML]{5CD0B3}{V_{\leq t}}\,\operatorname{softmax}\!\left(\frac{ \textcolor[HTML]{58C4DD}{K_{\leq t}^{\mathsf T}}\textcolor[HTML]{FFFF80}{\mathbf{q}_t} }{\sqrt{d_k}}\right)",
            size=52,
        ).move_to(DOWN*.25)
        if equation.width > 12:
            equation.scale_to_fit_width(12)
        principle = prose("Keep the past. Reuse it.", 43).move_to(UP*1.5)
        self.play(FadeOut(words),FadeOut(stems),FadeOut(cache_brace),FadeOut(cache_label),
                  ReplacementTransform(keys,colored_glyphs(equation,BLUE)),
                  ReplacementTransform(values,colored_glyphs(equation,TEAL)),run_time=1.8)
        self.play(Write(equation),FadeIn(principle),run_time=2)
        convention = prose("K and V collect token vectors as columns", 23, MUTED).move_to(DOWN*1.55)
        self.play(FadeIn(convention),run_time=.7)
        self.mark("attention-equation")
        self.wait(3)
        self.finish()


class Fragmentation(Chapter):
    number, heading = "02", "How much memory should we reserve?"

    def construct(self):
        self.caption("Suppose each request reserves twelve token slots, even though its final length is unknown.")
        rows, names = VGroup(), VGroup()
        lengths, colors = [6,3,5],[BLUE,TEAL,PURPLE]
        for i,(n,c) in enumerate(zip(lengths,colors)):
            row = MemoryBlock(list(range(n))+[None]*(12-n),c,width=7.8,height=.57).move_to([-1,1.65-i*1.1,0])
            rows.add(row)
            names.add(prose(chr(65+i),30,c).next_to(row,LEFT,buff=.4))
        self.play(LaggedStart(*[AnimationGroup(FadeIn(n),Create(r)) for n,r in zip(names,rows)],lag_ratio=.2),run_time=2)
        fraction = formula(r"\frac{14}{36}",size=68).move_to([4.6,.5,0])
        used = prose("used / reserved",23,MUTED).next_to(fraction,DOWN,buff=.3)
        self.play(Write(fraction),FadeIn(used),run_time=1.4)
        self.wait(3)
        self.caption("Cut the cache into blocks of four. Allocate only the blocks needed by the current tokens.")
        splits=VGroup()
        for row in rows:
            for i in [4,8]:
                x=row.cells[i].get_left()[0]
                splits.add(DashedLine([x,row.get_top()[1]+.13,0],[x,row.get_bottom()[1]-.13,0],color=GOLD,stroke_width=2,dash_length=.07))
        self.play(LaggedStart(*[Create(s) for s in splits],lag_ratio=.1),run_time=1.2)
        self.wait(1)
        blocks=VGroup()
        for n,c,row in zip(lengths,colors,rows):
            group=VGroup(*[MemoryBlock([k if k<n else None for k in range(i,i+4)],c,width=2.6,height=.57)
                           for i in range(0,n,4)]).arrange(RIGHT,buff=.35)
            group.move_to(row).align_to(row,LEFT)
            blocks.add(group)
        self.play(*[ReplacementTransform(row,group) for row,group in zip(rows,blocks)],FadeOut(splits),
                  TransformMatchingTex(fraction,formula(r"\frac{14}{20}",size=68).move_to(fraction)),
                  Transform(used,prose("used / allocated",23,TEAL).move_to(used)),run_time=2)
        self.wait(2)
        self.caption("The same fourteen tokens now occupy twenty slots. Only the final block of each request has slack.")
        tail_boxes=VGroup(*[SurroundingRectangle(group[-1],color=GOLD,buff=.08,stroke_width=2) for group in blocks])
        self.play(LaggedStart(*[Create(box) for box in tail_boxes],lag_ratio=.2),run_time=1.3)
        bound=formula(r"0\leq",r"w_{\mathrm{tail}}",r"\leq B-1",size=45).move_to(DOWN*1.85)
        bound[1].set_color(GOLD)
        self.play(Write(bound),run_time=1.5)
        note=prose("unused slots per sequence",25,MUTED).next_to(bound,DOWN,buff=.2)
        self.play(FadeIn(note),run_time=.6)
        self.mark("fragmentation-bound")
        self.wait(3)
        self.finish()


class BlockMapping(Chapter):
    number, heading = "03", "Order and location are different things"

    def construct(self):
        self.caption("A block table connects the token sequence to physical memory. Matching colors follow the same data.")
        colors=[BLUE,TEAL,PURPLE]
        logical=VGroup(*[MemoryBlock([t if t<10 else None for t in range(i*4,i*4+4)],c,width=2.65,height=.5)
                          .move_to([-4.65,1.45-i*1.15,0]) for i,c in enumerate(colors)])
        logical_names=VGroup(*[formula(rf"b={i}",size=24,color=c).next_to(block,UP,buff=.13)
                                for i,(block,c) in enumerate(zip(logical,colors))])
        logic_title=prose("Logical blocks",25).move_to([-4.65,2.35,0])
        table_title=prose("Block table",25).move_to([-.9,2.35,0])
        pool_title=prose("Physical memory",25).move_to([3.85,2.35,0])
        table=VGroup(*[code(f"{i}  →  {p}",25,c).move_to([-.9,1.45-i*1.15,0])
                       for i,(p,c) in enumerate(zip([7,2,5],colors))])
        table_bracket=VGroup(Line([-1.9,1.8,0],[-1.9,-1.3,0],color=EDGE),
                             Line([.1,1.8,0],[.1,-1.3,0],color=EDGE))
        pool=VGroup(*[MemoryBlock([None]*4,EDGE,width=2.55,height=.35).move_to([3.85,1.68-p*.46,0]) for p in range(8)])
        addresses=VGroup(*[code(f"P{p}",17,MUTED).next_to(block,RIGHT,buff=.16) for p,block in enumerate(pool)])
        self.play(FadeIn(logic_title),FadeIn(table_title),FadeIn(pool_title),FadeIn(logical),FadeIn(logical_names),
                  FadeIn(table),Create(table_bracket),FadeIn(pool),FadeIn(addresses),run_time=1.8)
        paths=VGroup()
        for i,p in enumerate([7,2,5]):
            filled=MemoryBlock([t if t<10 else None for t in range(i*4,i*4+4)],colors[i],width=2.55,height=.35).move_to(pool[p])
            path=arrow(table[i].get_right()+RIGHT*.1,pool[p].get_left(),colors[i],1.5)
            paths.add(path)
            self.play(GrowArrow(path),TransformFromCopy(logical[i],filled),FadeOut(pool[p]),
                      addresses[p].animate.set_color(colors[i]),run_time=1.2)
            pool[p]=filled
        self.wait(2)
        self.caption("For token six, divide by the block size. The quotient chooses a block; the remainder chooses a slot.")
        rule=formula(r"b=\left\lfloor\frac{t}{B}\right\rfloor",r",\qquad",r"r=t\bmod B",size=38).move_to(DOWN*2.2)
        self.play(Write(rule),run_time=1.6)
        concrete=formula(r"b=\left\lfloor\frac{6}{4}\right\rfloor=1",r",\qquad",r"r=6\bmod4=2",size=38).move_to(rule)
        concrete.set_color_by_tex("b=",TEAL)
        concrete.set_color_by_tex("r=",GOLD)
        self.play(TransformMatchingTex(rule,concrete),run_time=1.5)
        selected=SurroundingRectangle(logical[1].cells[2],color=GOLD,buff=.035,stroke_width=2.5)
        self.play(Create(selected),paths[0].animate.set_opacity(.2),paths[2].animate.set_opacity(.2),
                  paths[1].animate.set_color(GOLD).set_stroke(width=3),run_time=.8)
        self.wait(1)
        self.caption("Follow table[1] to physical block P2, then read slot 2. The logical token index is still six.")
        pulse=Dot(paths[1].get_start(),radius=.06,color=GOLD)
        self.add(pulse)
        self.play(MoveAlongPath(pulse,paths[1]),run_time=1.2,rate_func=linear)
        target=SurroundingRectangle(pool[2].cells[2],color=GOLD,buff=.04,stroke_width=2.5)
        lookup=code("table[1] = 2     →     P2[2]",23,GOLD).move_to(DOWN*2.85)
        self.play(FadeOut(pulse),TransformFromCopy(selected,target),Write(lookup),run_time=1)
        self.mark("address-translation")
        self.wait(3)
        self.finish()


class Attention(Chapter):
    number, heading = "04", "The addresses change. The mathematics stays."

    def construct(self):
        self.caption("The query compares with every valid key, even when those keys are stored in different physical blocks.")
        xs=np.linspace(-4.2,5.25,10)
        colors=[BLUE]*4+[TEAL]*4+[PURPLE]*2
        keys=VGroup(*[formula(rf"\mathbf{{k}}_{{{i}}}",size=32,color=c).move_to([x,.5,0])
                       for i,(x,c) in enumerate(zip(xs,colors))])
        query=formula(r"\mathbf{q}_t",size=48,color=GOLD).move_to([-5.7,.2,0])
        page_braces=VGroup(*[Brace(keys[a:b],UP,buff=.15,color=c) for a,b,c in [(0,4,BLUE),(4,8,TEAL),(8,10,PURPLE)]])
        page_names=VGroup(*[code(f"P{p}",17,c).next_to(brace,UP,buff=.1) for p,c,brace in zip([7,2,5],[BLUE,TEAL,PURPLE],page_braces)])
        score_rule=formula(r"s_i=\frac{ \textcolor[HTML]{FFFF80}{\mathbf{q}_t^{\mathsf T}}\textcolor[HTML]{58C4DD}{\mathbf{k}_i} }{\sqrt{d_k}}",size=42).move_to(UP*2.25)
        self.play(Write(score_rule),FadeIn(query),LaggedStart(*[Write(k) for k in keys],lag_ratio=.1),run_time=2)
        self.play(*[GrowFromCenter(b) for b in page_braces],FadeIn(page_names),run_time=.8)
        scores=np.array([.2,1.6,-.4,2.1,.8,-1.0,1.2,.3,-.6,1.8])
        dots=VGroup(*[Circle(radius=.08+.06*(s+1),stroke_width=0,fill_color=c,fill_opacity=.9).move_to([x,-.22,0])
                       for x,s,c in zip(xs,scores,colors)])
        numbers=VGroup(*[formula(f"{s:.1f}",size=25,color=c).move_to([x,-.94,0]) for x,s,c in zip(xs,scores,colors)])
        for a,b in [(0,4),(4,8),(8,10)]:
            route=CurvedArrow(query.get_right(),keys[a:b].get_bottom()+DOWN*.06,
                              angle=.25,color=GOLD,stroke_width=1.5,tip_length=.11)
            self.play(Create(route),LaggedStart(*[AnimationGroup(GrowFromCenter(dots[i]),Write(numbers[i]))
                                                for i in range(a,b)],lag_ratio=.15),run_time=1.5)
            self.play(FadeOut(route),run_time=.3)
        self.wait(2)
        self.caption("Softmax normalizes all of these scores together. Physical block boundaries do not split the denominator.")
        norm=formula(r"\alpha_i=\frac{\exp(s_i)}{\sum_{j=0}^{t}\exp(s_j)}",size=47).scale_to_fit_height(1.12).move_to(UP*2.05)
        norm.set_color(GOLD)
        self.play(ReplacementTransform(score_rule,norm),FadeOut(query),run_time=1.4)
        weights=np.exp(scores-scores.max()); weights/=weights.sum()
        new_numbers=VGroup(*[formula(f"{w:.2f}",size=25,color=GOLD).move_to(n) for w,n in zip(weights,numbers)])
        self.play(*[Transform(n,new) for n,new in zip(numbers,new_numbers)],
                  *[d.animate.scale(np.sqrt(w)*.8/d.radius).set_color(GOLD) for d,w in zip(dots,weights)],run_time=1.6)
        shared=Brace(numbers,DOWN,buff=.18,color=GOLD)
        shared_label=prose("one normalization across the entire context",24,GOLD).next_to(shared,DOWN,buff=.17)
        self.play(GrowFromCenter(shared),Write(shared_label),run_time=1.3)
        self.mark("global-softmax")
        self.wait(3)
        self.caption("Use these weights to mix the value vectors. Paging changes storage, while preserving the attention calculation.")
        result=formula(r"\mathbf{o}_t=\sum\nolimits_{i=0}^{t}",r"\alpha_i",r"\mathbf{v}_i",size=46).scale_to_fit_height(.85).move_to(DOWN*2.55)
        result[1].set_color(GOLD); result[2].set_color(TEAL)
        self.play(Write(result),run_time=1.5)
        self.mark("weighted-values")
        self.wait(3)
        self.finish()


class Allocation(Chapter):
    number, heading = "05", "Cross a boundary. Allocate one block."

    def construct(self):
        self.caption("At six tokens, the request owns two blocks. Appending token six writes into an existing slot.")
        first=MemoryBlock([0,1,2,3],BLUE,width=3.65,height=.62,address="P7").move_to([-3.9,1.55,0])
        tail=MemoryBlock([4,5,None,None],BLUE,width=3.65,height=.62,address="P2").move_to([-3.9,.12,0])
        empty=MemoryBlock([None]*4,EDGE,width=3.65,height=.62,address="P5 · free").move_to([-3.9,-1.32,0])
        code_lines=VGroup(*[code(line,20) for line in [
            "b, r = divmod(t, B)",
            "if r == 0:",
            "    table.append(allocate())",
            "cache[table[b]][r] = kv",
        ]]).arrange(DOWN,aligned_edge=LEFT,buff=.28).move_to([2.55,.2,0])
        code_lines[2].shift(RIGHT*.67)
        code_lines[1].set_color(PURPLE)
        code_lines[2].set_color(TEAL)
        cursor=SurroundingRectangle(code_lines[3],color=GOLD,buff=.1,stroke_width=1.2)
        current=code("t = 6   b = 1   r = 2",24,GOLD).move_to([2.6,1.8,0])
        table=code("table = [7, 2]",25,BLUE).move_to([0,-2.6,0])
        self.play(FadeIn(first),FadeIn(tail),FadeIn(empty),Write(code_lines),Write(current),Write(table),run_time=2)
        self.play(Create(cursor),run_time=.6)
        self.play(Transform(tail.contents[2],tail.put(2,6)),run_time=.8)
        self.wait(2)
        self.caption("Token seven fills the remaining slot. The block table is unchanged.")
        next_state=code("t = 7   b = 1   r = 3",24,GOLD).move_to(current)
        self.play(Transform(current,next_state),Transform(tail.contents[3],tail.put(3,7)),run_time=1.2)
        self.wait(2.5)
        self.caption("For token eight, the offset becomes zero. Allocate a free block, then extend the table.")
        boundary=code("t = 8   b = 2   r = 0",24,GOLD).move_to(current)
        self.play(Transform(current,boundary),Transform(cursor,SurroundingRectangle(code_lines[1:3],color=GOLD,buff=.12,stroke_width=1.2)),run_time=1.2)
        allocated=MemoryBlock([None]*4,BLUE,width=3.65,height=.62,address="P5").move_to(empty)
        extended=code("table = [7, 2, 5]",25,BLUE).move_to(table)
        self.play(Transform(empty,allocated),Transform(table,extended),run_time=1.3)
        self.play(Transform(cursor,SurroundingRectangle(code_lines[3],color=GOLD,buff=.1,stroke_width=1.2)),
                  Transform(empty.contents[0],empty.put(0,8,BLUE)),run_time=.8)
        self.mark("code-and-allocation")
        self.wait(3)
        self.caption("After the request finishes, its unshared blocks return to the pool and can serve another request.")
        release=code("release(table)",30,TEAL).move_to(code_lines)
        self.play(FadeOut(cursor),FadeOut(current),ReplacementTransform(code_lines,release),
                  *[Transform(block,MemoryBlock([None]*4,EDGE,width=3.65,height=.62,address=f"P{p} · free").move_to(block))
                    for block,p in zip([first,tail,empty],[7,2,5])],FadeOut(table),run_time=1.8)
        self.wait(2)
        self.finish()


class Sharing(Chapter):
    number, heading = "06", "A shared past. Two different futures."

    def construct(self):
        self.caption("Two continuations can share prefix blocks. Reference counts record how many requests still need each block.")
        a=VGroup(prose("Continuation A",28,BLUE),code("[7, 2]",23,BLUE)).arrange(DOWN,buff=.17).move_to([-4.95,1.1,0])
        b=VGroup(prose("Continuation B",28,PURPLE),code("[7, 2]",23,PURPLE)).arrange(DOWN,buff=.17).move_to([-4.95,-1.1,0])
        full=MemoryBlock([0,1,2,3],TEAL,width=2.6,height=.6,address="P7").move_to([-.5,1.15,0])
        tail=MemoryBlock([4,5,None,None],GOLD,width=2.6,height=.6,address="P2").move_to([3.6,1.15,0])
        ref_full=code("refs = 2",17,TEAL).next_to(full,DOWN,buff=.17)
        ref_tail=code("refs = 2",17,GOLD).next_to(tail,DOWN,buff=.17)
        routes=VGroup()
        for request,c in [(a,BLUE),(b,PURPLE)]:
            routes.add(arrow(request.get_right(),full.outline.get_left(),c,1.6))
            routes.add(CurvedArrow(request.get_right()+RIGHT*.1,tail.outline.get_left()+LEFT*.1,
                                    angle=-.42 if request is a else .35,color=c,stroke_width=1.6,tip_length=.12))
        self.play(FadeIn(a),FadeIn(b),FadeIn(full),FadeIn(tail),FadeIn(ref_full),FadeIn(ref_tail),run_time=1.6)
        self.play(LaggedStart(*[Create(r) for r in routes],lag_ratio=.18),run_time=1.5)
        self.wait(3)
        self.caption("A is about to append into a shared partial block. First copy that block; then change only A’s table.")
        private=MemoryBlock([4,5,None,None],BLUE,width=2.6,height=.6,address="P5").move_to([3.6,-1.2,0])
        copy_arrow=arrow(tail.get_bottom()+DOWN*.32,private.get_top(),MUTED,1.4)
        copy_text=prose("copy",22,MUTED).next_to(copy_arrow,RIGHT,buff=.15)
        self.play(GrowArrow(copy_arrow),FadeIn(copy_text),TransformFromCopy(tail,private),run_time=1.8)
        new_route=arrow(a.get_right(),private.outline.get_left(),BLUE,1.6)
        private_ref=code("refs = 1",17,BLUE).next_to(private,DOWN,buff=.17)
        self.play(ReplacementTransform(routes[1],new_route),Transform(a[1],code("[7, 5]",23,BLUE).move_to(a[1])),
                  Transform(ref_tail,code("refs = 1",17,GOLD).move_to(ref_tail)),FadeIn(private_ref),run_time=1.4)
        self.play(FadeOut(copy_arrow),FadeOut(copy_text),run_time=.5)
        self.wait(1.5)
        self.caption("Now A can write token six into its private copy. B’s data stays unchanged, and the full prefix remains shared.")
        self.play(Transform(private.contents[2],private.put(2,6)),run_time=1)
        self.play(Indicate(tail,color=GOLD,scale_factor=1.04),Indicate(full,color=TEAL,scale_factor=1.04),run_time=1)
        self.mark("copy-on-write")
        self.wait(3)
        conclusion=prose("Logical continuity. Physical freedom.",37).move_to(DOWN*2.6)
        self.caption("PagedAttention keeps token order intact while making GPU memory easier to allocate, reuse, and share.")
        self.play(Write(conclusion),run_time=1.5)
        self.wait(3)
        self.finish()
