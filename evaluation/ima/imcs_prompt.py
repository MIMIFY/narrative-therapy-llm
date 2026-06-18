import json
import yaml

# 添加IMCS标注示例,用于few-shot学习
IMCS_EXAMPLES = [
    {
        "context": [
            "Therapist: 你最近在工作和生活上有什么变化吗？",
            "Client: 工作上还是老样子，每天按部就班地完成工作。",
            "Therapist: 那在生活方面呢？有没有什么新的尝试或者改变？",
            "Client: 生活上也没什么特别的，就是每天上下班，回家看看电视，周末偶尔和朋友吃个饭。"
        ],
        "client_utterance": "其实我觉得现在的生活也挺好的，虽然没什么特别的变化，但至少很稳定。工作虽然有点累，但收入还不错，能养活自己。周末和朋友聚聚，聊聊天，也挺开心的。",
        "annotation": {
            "annotation": "None",
            "resource": "None",
            "confidence": "0.98",
            "latent_narrative_dynamics_analysis": "维持现状的稳定叙事/保持原有角色定位/缺乏新的发展路径"
        }
    },
    {
        "context": [
            "Therapist: 你之前提到过,在遭受家暴之后,出现在开阔或公共的地方让你感到不安全. ",
            "Client: 是的,在和前伴侣发生那些事之后,每次想到要出门我就紧张,就连去超市我都觉得很难承受,特别是人多的时候. ",
            "Therapist: 踏出这一步（不再遵循\"恐惧\"的规则,走出去）对你来说困难吗？有没有哪一次,即使感到害怕,也还是做了点不同的事情？比如走出去了？"
        ],
        "client_utterance": "昨天我去电影院看了一场电影,这是我这个月第一次出门！",
        "annotation": {
            "annotation": "<Action I>昨天我去电影院看了一场电影,这是我这个月第一次出门！</Action I>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.95",
            "latent_narrative_dynamics_analysis": "治疗师提出具体引导后,来访者展开叙述打破封闭状态的行为/行动体现对问题模式的主动挑战/显示出自我选择与突破"
        }
    },
    {
        "context": [
            "Client: 我开始在想,如果我继续放任我的抑郁,会发生什么. ",
            "Therapist: 你是不是开始察觉,抑郁其实在你生活中扮演着一种'隐藏的操控者'？",
            "Client: 是的,确实是这样. ",
            "Therapist: 那你觉得抑郁到底想从你这里得到什么？你是否觉得它是想要控制你的人生,让你无法享受生活中开心的时刻呢？"
        ],
        "client_utterance": "是的,我是这么认为的. 它想控制我整个人生,最后把我的人生整个夺走. ",
        "annotation": {
            "annotation": "<Reflection I>它想控制我整个人生,最后把我的人生整个夺走. </Reflection I>",
            "resource": "therapist-initiated, client-accepted",
            "confidence": "0.93",
            "latent_narrative_dynamics_analysis": "来访者通过与抑郁'对话'的方式揭示其控制性本质/叙事从症状经验转向具象的意义建构/出现对问题模式背后深层作用的意识觉醒"
        }
    },
    {
        "context": [
            "Therapist: 你说最近有点孤单,可以和我分享一下孤单的感受吗？",
            "Client: 是的,我有几个朋友约我,但我总觉得自己不合群,怕自己说错话. ",
            "Therapist: 那你有没有重新想过这种顾虑从何而来？"
        ],
        "client_utterance": "我意识到我一直假设别人不喜欢我,其实只是我太敏感了. 于是我发了条信息给以前的朋友,约她出来喝咖啡,虽然一开始很紧张,但我们聊得很自然. ",
        "annotation": {
            "annotation": "<Reflection I>我意识到我一直假设别人不喜欢我,其实只是我太敏感了. </Reflection I><Action I>于是我发了条信息给以前的朋友,约她出来喝咖啡,虽然一开始很紧张,但我们聊得很自然. </Action I>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.90",
            "latent_narrative_dynamics_analysis": "来访者觉察社交恐惧的根源在于自我假设,而非客观事实/通过主动联系朋友打破回避模式/主动迈出连接,建立起正向社交体验基础"
        }
    },
    {
        "context": [
            "Client: 我之所以提起这件事,是想说明我这些年都在努力去争取……",
            "Therapist: 争取的是摆脱'你必须按你父母期待的方式生活'这个信念？",
            "Client: 是的,我一直在试图改变自己,去取悦他们. 但现在我越来越觉得这样做根本没有意义. ",
            "Therapist: 这样的努力让你不断否定真实的自己,不断调整情绪和想法,去贴合他们的期待……"
        ],
        "client_utterance": "没错. 我真的已经受够了. 我再也忍不了这种状态了. 说到底,父母本应该是爱孩子的,而不是整天评判他们. ",
        "annotation": {
            "annotation": "<Protest I>没错. 我真的已经受够了. 我再也忍不了这种状态了. 说到底,父母本应该是爱孩子的,而不是整天评判他们. </Protest I>",
            "resource": "client-generated",
            "confidence": "0.97",
            "latent_narrative_dynamics_analysis": "来访者意识到自身长期受制于父母的批判性期待/情绪性反应伴随价值判断构成主动反抗/从被动迎合转为拒绝接受内化的否定立场"
        }
    },
    {
        "context": [
            "Therapist: 最近你说你更敢表达了,也试着主动和人接触了. ",
            "Client: 是的,我现在不会像以前那样总是退缩了. ",
            "Therapist: 你有没有想过,把这种改变带到其他生活领域？比如关系或者职业方面？"
        ],
        "client_utterance": "我报名参加了单位的跨部门项目组,想试试看能不能承担一个小组协调的角色. 我觉得如果能练习带领团队,也许未来我能考虑申请管理岗. ",
        "annotation": {
            "annotation": "<Action II>我报名参加了单位的跨部门项目组,想试试看能不能承担一个小组协调的角色. 我觉得如果能练习带领团队,也许未来我能考虑申请管理岗. </Action II>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.92",
            "latent_narrative_dynamics_analysis": "来访者将自我效能的觉察延伸到职业角色/通过计划新挑战体现行为上的一般化/行为推动未来身份可能性的重塑"
        }
    },
    {
        "context": [
            "Therapist: 你上次提到,最近面对压力的方式似乎变得不同了. ",
            "Client: 是的,我自己也注意到了. ",
            "Therapist: 如果是以前的你,会怎么处理？而现在又是什么样的？"
        ],
        "client_utterance": "以前遇到一点问题我就会一整天焦虑、否定自己,甚至想逃避. 但这次我主动找朋友聊了聊,还列了一个小计划. 我突然意识到,我不再那么容易被打倒了. ",
        "annotation": {
            "annotation": "<Reflection II>以前遇到一点问题我就会一整天焦虑、否定自己,甚至想逃避. </Reflection II><Action II>但这次我主动找朋友聊了聊,我告诉自己这是正常的,深呼吸然后开始做事情就不焦虑了. 我打算把每一次战胜的时刻记录在日记本上,以后继续尝试一些我之前回避的事. </Action II><Reflection II>我突然意识到,我不再那么容易被打倒了. </Reflection II>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.88",
            "latent_narrative_dynamics_analysis": "来访者通过与过去自我的对比觉察到身份变化/情绪调节与行动策略均显成熟/叙事焦点从'脆弱受害者'向'主动修复者'转变"
        }
    },
    {
        "context": [
            "Therapist: 你最近提到在人际关系中感受到了一些变化,能说说发生了什么吗？",
            "Client: 以前我总是害怕拒绝别人,哪怕自己很不舒服也会勉强答应. ",
            "Therapist: 那这段时间你是怎么处理类似的情境的？"
        ],
        "client_utterance": "我发现我已经不像以前那样压抑自己了. 上周有个朋友临时让我帮他写方案,以前我肯定会答应,但这次我告诉他我有自己的安排,不能接这个活. 说出来之后我一点也不觉得愧疚,反而松了一口气. 我觉得我真的在改变,所以我也打算把这个界限意识带到工作中,比如不再默默加班、开始主动安排自己的时间. ",
        "annotation": {
            "annotation": "<Reflection II>我发现我已经不像以前那样压抑自己了. 上周有个朋友临时让我帮他写方案,以前我肯定会答应,但这次我告诉他我有自己的安排,不能接这个活. 说出来之后我一点也不觉得愧疚,反而松了一口气. </Reflection II><Action II>我也打算把这个界限意识带到工作中,比如不再默默加班、开始主动安排自己的时间. </Action II>",
            "resource": "client-generated",
            "confidence": "0.94",
            "latent_narrative_dynamics_analysis": "来访者明确对比了过去顺从型的自我与现在有边界感的自我/觉察改变过程并体验积极内在反馈/将边界意识推广至职场领域,体现出行为转变的未来导向和扩展性"
        }
    },
    {
        "context": [
            "Client: 我以前活得太压抑了，我从小就觉得要先顾好别人,自己才有资格被爱. ",
            "Therapist: 听起来你在不停地压抑自己的感受和需求. ",
            "Therapist: 那你现在怎么看待自己的这些需求呢？"
        ],
        "client_utterance": "我觉得我的感受也是重要的. 我有权利说'不',有权利累了就休息,而不是一味迎合别人. 我想开始为我自己活,而不是活在别人期望里. ",
        "annotation": {
            "annotation": "<Protest II>我觉得我的感受也是重要的. 我有权利说'不',有权利累了就休息,而不是一味迎合别人. 我想开始为我自己活,而不是活在别人期望里. </Protest II>",
            "resource": "client-generated",
            "confidence": "0.96",
            "latent_narrative_dynamics_analysis": "来访者肯定自身需求并建立边界/表达了主动拒绝和自我照顾的权利/叙事中展现身份位置从顺从者转向拥有主体性的行动者"
        }
    }
]

# 添加英文版IMCS标注示例
IMCS_EXAMPLES_en = [
    {
        "context": [
            "Therapist: Have there been any changes in your work and life recently?",
            "Client: Work is still the same, just completing tasks routinely every day.",
            "Therapist: What about in your personal life? Any new attempts or changes?",
            "Client: Nothing special in my personal life either, just commuting to work, watching TV at home, and occasionally having meals with friends on weekends."
        ],
        "client_utterance": "Actually, I think my current life is quite good. Although there haven't been any special changes, at least it's stable. Work is a bit tiring, but the income is good enough to support myself. Meeting friends on weekends and chatting is also quite enjoyable.",
        "annotation": {
            "annotation": "None",
            "resource": "None",
            "confidence": "0.98",
            "latent_narrative_dynamics_analysis": "Maintaining a stable narrative of the status quo/Retaining the original role positioning/Lacking new developmental paths"
        }
    },
    {
        "context": [
            "Therapist: You mentioned before that after experiencing domestic violence, being in open or public places makes you feel unsafe.",
            "Client: Yes, after what happened with my ex-partner, I get nervous every time I think about going out. Even going to the supermarket feels overwhelming, especially when it's crowded.",
            "Therapist: Was it difficult for you to take this step (breaking the 'fear' rule and going out)? Was there any time when, despite feeling afraid, you still did something different? Like going out?"
        ],
        "client_utterance": "Yesterday I went to the cinema to watch a movie, it was my first time going out this month!",
        "annotation": {
            "annotation": "<Action I>Yesterday I went to the cinema to watch a movie, it was my first time going out this month!</Action I>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.95",
            "latent_narrative_dynamics_analysis": "After therapist's specific guidance, client describes behavior breaking isolation/Action demonstrates active challenge to problem pattern/Shows self-choice and breakthrough"
        }
    },
    {
        "context": [
            "Client: I've started thinking about what would happen if I continue to let my depression take over.",
            "Therapist: Are you beginning to realize that depression actually plays the role of a 'hidden manipulator' in your life?",
            "Client: Yes, that's exactly how it is.",
            "Therapist: What do you think depression wants from you? Do you feel it wants to control your life, preventing you from enjoying happy moments?"
        ],
        "client_utterance": "Yes, that's what I think. It wants to control my entire life, eventually taking it all away.",
        "annotation": {
            "annotation": "<Reflection I>It wants to control my entire life, eventually taking it all away.</Reflection I>",
            "resource": "therapist-initiated, client-accepted",
            "confidence": "0.93",
            "latent_narrative_dynamics_analysis": "Client reveals controlling nature through 'dialogue' with depression/Narrative shifts from symptom experience to concrete meaning construction/Emergence of awareness about deep-seated effects of problem pattern"
        }
    },
    {
        "context": [
            "Therapist: You mentioned feeling lonely recently, could you share your feelings about loneliness?",
            "Client: Yes, some friends invited me out, but I always feel like I don't fit in, afraid of saying the wrong thing.",
            "Therapist: Have you reconsidered where this concern comes from?"
        ],
        "client_utterance": "I realized I've been assuming others don't like me, but actually I'm just being too sensitive. So I sent a message to an old friend, inviting her for coffee. Although I was nervous at first, we had a natural conversation.",
        "annotation": {
            "annotation": "<Reflection I>I realized I've been assuming others don't like me, but actually I'm just being too sensitive.</Reflection I><Action I>So I sent a message to an old friend, inviting her for coffee. Although I was nervous at first, we had a natural conversation.</Action I>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.90",
            "latent_narrative_dynamics_analysis": "Client recognizes social anxiety stems from self-assumptions rather than objective facts/Breaks avoidance pattern through active friend contact/Establishes foundation for positive social experience through proactive connection"
        }
    },
    {
        "context": [
            "Client: The reason I brought this up is to show how I've been trying to fight for...",
            "Therapist: Fight against the belief that 'you must live according to your parents' expectations'?",
            "Client: Yes, I've been trying to change myself to please them. But now I increasingly feel this is meaningless.",
            "Therapist: This effort has made you constantly deny your true self, constantly adjusting emotions and thoughts to meet their expectations..."
        ],
        "client_utterance": "Exactly. I've really had enough. I can't stand this state anymore. After all, parents should love their children, not constantly judge them.",
        "annotation": {
            "annotation": "<Protest I>Exactly. I've really had enough. I can't stand this state anymore. After all, parents should love their children, not constantly judge them.</Protest I>",
            "resource": "client-generated",
            "confidence": "0.97",
            "latent_narrative_dynamics_analysis": "Client recognizes long-term subjection to parents' critical expectations/Emotional response with value judgment constitutes active resistance/Shift from passive compliance to rejection of internalized negative stance"
        }
    },
    {
        "context": [
            "Therapist: Recently you mentioned being more willing to express yourself and trying to actively connect with others.",
            "Client: Yes, I don't withdraw like before anymore.",
            "Therapist: Have you thought about bringing this change to other areas of life? Like relationships or career?"
        ],
        "client_utterance": "I joined the cross-department project team at work, trying to take on a team coordination role. I think if I can practice leading a team, maybe I can consider applying for a management position in the future.",
        "annotation": {
            "annotation": "<Action II>I joined the cross-department project team at work, trying to take on a team coordination role. I think if I can practice leading a team, maybe I can consider applying for a management position in the future.</Action II>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.92",
            "latent_narrative_dynamics_analysis": "Client extends self-efficacy awareness to professional role/Demonstrates behavioral generalization through planning new challenges/Behavior promotes reshaping of future identity possibilities"
        }
    },
    {
        "context": [
            "Therapist: You mentioned last time that your way of handling pressure seems different now.",
            "Client: Yes, I've noticed that myself.",
            "Therapist: How would you have handled it before? And how is it different now?"
        ],
        "client_utterance": "Before, when I encountered any problem, I would spend the whole day anxious, self-critical, even wanting to escape. But this time I actively talked to a friend and made a small plan. I suddenly realized I'm not so easily defeated anymore.",
        "annotation": {
            "annotation": "<Reflection II>Before, when I encountered any problem, I would spend the whole day anxious, self-critical, even wanting to escape.</Reflection II><Action II>But this time I actively talked to a friend and made a small plan. I told myself this is normal, took deep breaths and started doing things, then the anxiety went away. I plan to record every victorious moment in my journal and continue trying things I used to avoid.</Action II><Reflection II>I suddenly realized I'm not so easily defeated anymore.</Reflection II>",
            "resource": "therapist-prompted, client-elaborated",
            "confidence": "0.88",
            "latent_narrative_dynamics_analysis": "Client perceives identity change through comparison with past self/Emotional regulation and action strategies show maturity/Narrative focus shifts from 'vulnerable victim' to 'active repairer'"
        }
    },
    {
        "context": [
            "Therapist: You mentioned feeling some changes in your relationships recently, could you tell me what happened?",
            "Client: Before, I was always afraid to say no to others, even when I was very uncomfortable, I would force myself to agree.",
            "Therapist: How have you been handling similar situations during this time?"
        ],
        "client_utterance": "I've noticed I'm not suppressing myself like before. Last week a friend asked me to help with a proposal, and while I would have agreed before, this time I told him I had my own plans and couldn't take it on. After saying it, I didn't feel guilty at all, but rather relieved. I think I'm really changing, so I also plan to bring this boundary awareness to work, like no longer working overtime silently and starting to actively arrange my own time.",
        "annotation": {
            "annotation": "<Reflection II>I've noticed I'm not suppressing myself like before. Last week a friend asked me to help with a proposal, and while I would have agreed before, this time I told him I had my own plans and couldn't take it on. After saying it, I didn't feel guilty at all, but rather relieved.</Reflection II><Action II>I also plan to bring this boundary awareness to work, like no longer working overtime silently and starting to actively arrange my own time.</Action II>",
            "resource": "client-generated",
            "confidence": "0.94",
            "latent_narrative_dynamics_analysis": "Client clearly contrasts past compliant self with present boundary-aware self/Perceives change process and experiences positive internal feedback/Extends boundary awareness to workplace, showing future-oriented and expansive nature of behavioral change"
        }
    },
    {
        "context": [
            "Client: I used to live too repressed, since childhood I felt I had to take care of others first to deserve love.",
            "Therapist: It sounds like you've been constantly suppressing your feelings and needs.",
            "Therapist: How do you view these needs of yours now?"
        ],
        "client_utterance": "I think my feelings are important too. I have the right to say 'no', the right to rest when tired, rather than constantly pleasing others. I want to start living for myself, not according to others' expectations.",
        "annotation": {
            "annotation": "<Protest II>I think my feelings are important too. I have the right to say 'no', the right to rest when tired, rather than constantly pleasing others. I want to start living for myself, not according to others' expectations.</Protest II>",
            "resource": "client-generated",
            "confidence": "0.96",
            "latent_narrative_dynamics_analysis": "Client affirms own needs and establishes boundaries/Expresses right to actively refuse and self-care/Narrative shows identity position shifting from compliant to agentic actor"
        }
    }
]

def build_prompt(context: list, language: str, client_utterance: str, examples: list = IMCS_EXAMPLES, examples_en: list = IMCS_EXAMPLES_en) -> str:
    """
    拼接IMCS标注示例，用于few-shot学习。
    每个示例用<example>标签包裹，包含上下文和当前发言。
    """
    if language != 'zh' and language != 'en':
        raise ValueError(f"Language {language} is not supported")
        return ""
    # 根据语言选择示例和类别
    selected_examples = examples if language == 'zh' else examples_en
    # selected_categories = categories if language == 'zh' else categories_en
    
    # 构建few-shot示例字符串
    examples_str = "\n\n".join([
        f"<example {i+1}>\n[Dialogue history]:\n" + "\n".join(example['context']) + 
        f"\n[Client utterance]:\n{example['client_utterance']}\n\n[output]:\n```YAML\n{yaml.dump(example['annotation'], allow_unicode=True, sort_keys=False)}\n```\n</example {i+1}>"
        for i, example in enumerate(selected_examples)
    ])
    
    # # 构建类别定义字符串
    # categories_str = "\n\n".join([
    #     f"### {category['name']}\n"
    #     f"- Definition: {category['definition']}\n"
    #     f"- Contents: {category['contents']}\n"
    #     f"- Example: {category['example']}"
    #     for category in selected_categories
    # ])
    
    # 构建当前对话的上下文
    context_str = "\n".join(context)
    
    user_prompt = f"""# IMCS标注任务\n
## 标注示例
{examples_str}\n
#请你遵循IMCS的编码规则进行标注:
## [Dialogue history]:
{context_str}\n
## [Client utterance]:
{client_utterance}\n
## [output]:
"""

    user_prompt_en = f"""# IMCS Annotation Task\n
## Annotation Examples
{examples_str}\n
# Please follow IMCS coding rules for annotation:
## [Dialogue history]:
{context_str}\n
## [Client utterance]:
{client_utterance}\n
## [output]:
"""
    if language == 'zh':
        return user_prompt
    else:
        return user_prompt_en

# IMCS的system_prompt
IMCS_system_prompt = """你是一位遵循《IMCS（Innovative Moments Coding System）》标准的心理治疗语言标注专家,目标是对来访者的治疗性对话片段进行IM（创新时刻）类型的精确编码,并进行简洁有力的叙事动力学分析. 请遵循以下标准:

# 一、IMCS标准定义
## 1.1 创新时刻（IM）定义
创新时刻（Innovative Moments, IM）是指来访者在治疗对话中出现的、与主导问题叙事相异的时刻。这些时刻代表了来访者开始质疑、挑战或改变其问题叙事的方式。

## 1.2 IMCS编码系统
### Level 1: 与问题叙事创建距离
#### *Action I*
- 定义：为克服问题而采取或打算采取的行动
- 核心特征：新的行为策略、主动探索解决方案、寻找问题相关信息
- 示例：<Action I>昨天我去电影院看了一场电影,这是我这个月第一次出门！</Action I>

#### *Reflection I*
- 定义：对问题有新的理解或重新思考
- 核心特征：重新考虑问题的原因、意识到其影响、新的问题表述、适应性自我指导
- 示例：<Reflection I>抑郁它想控制我整个人生,最后把我的人生整个夺走. </Reflection I>

#### *Protest I*
- 定义：对问题及其假设提出反对
- 核心特征：拒绝或反对问题、批判支持问题的人、批判自我的问题方面
- 示例：<Protest I>没错. 我真的已经受够了. 我再也忍不了这种状态了. 说到底,父母本应该是爱孩子的,而不是整天评判他们. 我不会改变自己来迎合他们了。 </Protest I>

### Level 2: 以变化为中心
#### *Action II*
- 定义：将积极变化推广到未来或其他生活领域
- 核心特征：投资新项目、投资新关系、发展与问题无关的新技能，将问题经验拓展为新情况下的资源
- 示例：<Action II>我报名参加了单位的跨部门项目组,想试试看能不能承担一个小组协调的角色. 我觉得如果能练习带领团队,也许未来我能考虑申请管理岗. </Action II>

#### *Reflection II*
- 定义：对比自我（什么改变了？）或自我转变（如何/为什么变化发生了？）
- 核心特征：跨时间对比自我位置、解决过去内部或关系冲突、观察进步
- 示例：<Reflection II>我发现我已经不像以前那样压抑自己了. 上周有个朋友临时让我帮他写方案,以前我肯定会答应,但这次我告诉他我有自己的安排,不能接这个活. 说出来之后我一点也不觉得愧疚,反而松了一口气. </Reflection II>

#### *Protest II*
- 定义：自我肯定与赋权
- 核心特征：以自我为中心、肯定个人权利、需求和价值
- 示例：<Protest II>我觉得我的感受也是重要的. 我有权利说'不',有权利累了就休息,而不是一味迎合别人. 我想开始为我自己活,而不是活在别人期望里. </Protest II>

# 二、编码规则与标准
## 2.1 基本规则
- 当Action和Reflection同时存在时，分别编码
- 当Action或Reflection（或两者）与Protest重叠时，编码为Protest
- 确保标注的IM内容完整且准确
- 当来访者的发言没有表现出任何IM特征时，标注为"None"，并在叙事动力学分析中说明原因

## 2.2 标注要求
- 精准定位来访者的发言范围
- 使用<IM类型>......</IM类型>格式
- 保证语言完整、含义清晰
- 不可截断关键句
- 当没有IM时，annotation和resource字段均填写"None"

## 2.3 资源类型
1. *client-generated*：来访者主动生成、无引导
2. *therapist-prompted, client-elaborated*：治疗师提问或引导，来访者展开
3. *therapist-initiated, client-accepted*：治疗师提供明确内容或框架，来访者表示接受

# 三、叙事动力学分析框架
## 3.1 主导叙事变化
- 原有的负面/限制性叙事发生了怎样的转变？
- 新的叙事主题是什么？
- 叙事结构如何重组？

## 3.2 自我身份变化
- 来访者的自我定位是否发生变化？
- 从什么身份转变为什么身份？
- 新的自我认同如何形成？

## 3.3 未来可能性
- 此次IM是否为新的可能性打开了路径？
- 在行为、关系、价值上有何扩展？
- 未来发展的方向是什么？

# 四、输出格式
请使用以下YAML格式输出标注结果：
```YAML
annotation: <IM type annotation>
resource: <IM type resource>
confidence: <confidence score>
latent_narrative_dynamics_analysis: <analysis text>
```

# 五、注意事项
1. 标注时必须结合上下文，理解对话的整体脉络
2. 确保标注的IM内容完整，不要截断句子
3. 叙事动力学分析要具体且有针对性，非常简洁明确
4. 当不确定时，可以给出较低的置信度
5. 如果一轮对话中出现多个IM，需要分别标注
6. 标注要非常合情合理
7. 当来访者的发言只是描述现状、表达感受或进行日常对话，没有表现出对问题的反思、行动或抗议，也没有体现出自我身份的变化或未来发展的可能性时，应标注为"None"
"""


IMCS_system_prompt_en = """You are a professional psychotherapeutic language annotation expert following the IMCS (Innovative Moments Coding System) standard. Your goal is to precisely code IM (Innovative Moments) types in client's therapeutic dialogue segments and provide concise and powerful narrative dynamics analysis. Please follow these standards:

# 1. IMCS Standard Definitions
## 1.1 Definition of Innovative Moments (IM)
Innovative Moments (IM) are moments in therapeutic dialogue where the client's narrative differs from the dominant problem narrative. These moments represent the client's beginning to question, challenge, or change their problem narrative.

## 1.2 IMCS Coding System
### Level 1: Creating Distance from the Problem
#### *Action I*
- Definition: Actions taken or intended to overcome the problem
- Core Features: New behavioral strategies, active exploration of solutions, searching for problem-related information
- Example: <Action I>Yesterday I went to the cinema for the first time in months!</Action I>

#### *Reflection I*
- Definition: New understanding or rethinking of the problem
- Core Features: Reconsidering problem causes, awareness of effects, new problem formulations, adaptive self-instructions
- Example: <Reflection I>Depression wants to control my entire life, eventually taking it all away.</Reflection I>

#### *Protest I*
- Definition: Objecting to the problem and its assumptions
- Core Features: Rejecting or opposing the problem, criticizing those who support it, criticizing problematic aspects of self
- Example: <Protest I>That's right. I've had enough. I can't stand this state anymore. After all, parents should love their children, not constantly judge them. I won't change myself to please them anymore.</Protest I>

### Level 2: Centered on the Change
#### *Action II*
- Definition: Generalizing positive changes to future or other life dimensions
- Core Features: Investing in new projects, investing in new relationships, developing skills unrelated to the problem
- Example: <Action II>I joined the cross-department project team at work, trying to take on a team coordination role. I think if I can practice leading a team, maybe I can consider applying for a management position in the future.</Action II>

#### *Reflection II*
- Definition: Contrasting self (what changed?) or self-transformation (how/why change occurred?)
- Core Features: Contrasting self-positions across time, resolving past internal or relational conflicts, observing progress
- Example: <Reflection II>I've noticed I'm not suppressing myself like before. Last week a friend asked me to help with a proposal, and while I would have agreed before, this time I told him I had my own plans and couldn't take it on. After saying it, I didn't feel guilty at all, but rather relieved.</Reflection II>

#### *Protest II*
- Definition: Self-affirmation and empowerment
- Core Features: Centering on the self, affirming personal rights, needs, and values
- Example: <Protest II>I think my feelings are important too. I have the right to say 'no', the right to rest when tired, rather than constantly pleasing others. I want to start living for myself, not according to others' expectations.</Protest II>

# 2. Coding Rules and Standards
## 2.1 Basic Rules
- When Action and Reflection coexist, code them separately
- When Action or Reflection (or both) overlap with Protest, code as Protest
- Ensure IM content is complete and accurate
- When the client's speech does not exhibit any IM characteristics, it should be annotated as "None" and the reason should be explained in the narrative dynamics analysis

## 2.2 Annotation Requirements
- Precisely locate the client's speech range
- Use <IM type>......</IM type> format
- Ensure language is complete and meaning is clear
- Do not truncate key sentences
- When there is no IM, both the annotation and resource fields should be filled with "None"

## 2.3 Resource Types
1. *client-generated*: Client actively generates without guidance
2. *therapist-prompted, client-elaborated*: Therapist questions or guides, client elaborates
3. *therapist-initiated, client-accepted*: Therapist provides explicit content or framework, client accepts

# 3. Narrative Dynamics Analysis Framework
## 3.1 Dominant Narrative Change
- How has the original negative/restrictive narrative transformed?
- What is the new narrative theme?
- How has the narrative structure been reorganized?

## 3.2 Self-Identity Change
- Has the client's self-positioning changed?
- From what identity to what identity?
- How has the new self-identity formed?

## 3.3 Future Possibilities
- Has this IM opened paths to new possibilities?
- What expansions are there in behavior, relationships, and values?
- What is the direction of future development?

# 4. Output Format
Please use the following YAML format for output:
```YAML
annotation: <IM type annotation>
resource: <IM type resource>
confidence: <confidence score>
latent_narrative_dynamics_analysis: <analysis text>
```

# 5. Important Notes
- Annotation must consider context and understand the overall dialogue flow
- Ensure IM content is complete, do not truncate sentences
- Narrative dynamics analysis should be specific and targeted, very concise and clear
- When uncertain, provide lower confidence scores
- If multiple IMs appear in one dialogue turn, code them separately
- Annotation must be very strict
- When the client's speech merely describes the current situation, expresses feelings, or engages in daily conversation without reflecting on the problem, taking action, or protesting, and does not indicate a change in self-identity or future possibilities, it should be annotated as "None"
"""

# IMCS类别结构化定义与Prompt拼接

IMCS_CATEGORIES = [
    {
        "name": "Action I",
        "definition": "Performed and intended actions to overcome the problem.",
        "definition-zh": "为克服问题而采取或打算采取的行动. ",
        "contents": "New behavioral strategies to overcome the problem, active exploration of solutions, and searching for information about the problem.",
        "contents-zh": "克服问题的新行为策略,积极探索解决方案,并寻找有关问题的信息.",
        "example": "Client: 'Yesterday, I went to the cinema for the first time in months!'",
        "chinese_example": "来访者:'昨天我第一次主动去健身房锻炼. '"
    },
    {
        "name": "Reflection I",
        "definition": "New understanding or rethinking of the problem.",
        "definition-zh": "对问题有新的理解或重新思考. ",
        "contents": "Reconsidering the problem's causes, awareness of its effects, new problem formulations, adaptive self-instructions and thoughts, intention to fight (CONTEST) the problem's demands, and references to self-worth and/or feelings of well-being.",
        "contents-zh": "重新考虑问题的成因,意识到其影响,提出新的问题表述,适应性自我指导和思考,决心对抗问题,并提及自我价值或/和良好的感受.",
        "example": "Client: 'I realize that the more I isolate myself, the more depression gets overwhelming...'",
        "chinese_example": "来访者:'我发现越是逃避,焦虑反而更严重. '"
    },
    {
        "name": "Protest I",
        "definition": "Objecting to the problem and its assumptions.",
        "definition-zh": "对问题及其假设提出反对. ",
        "contents": "Rejecting or objecting to the problem, critique of those who support it, and critique of problematic facets of the self.",
        "contents-zh": "拒绝或反对问题,批判支持这个问题的人,批判问题的负面方面.",
        "example": "Client: 'I won't let my fear of others destroy my life.'",
        "chinese_example": "来访者:'我不想再被这些负面想法控制了！'"
    },
    {
        "name": "Action II",    
        "definition": "Generalization into the future and other life dimensions of good outcomes (performed or projected actions).",
        "definition-zh": "将积极变化推广到未来或其他生活领域. ",
        "contents": "Investment in new projects, investment in new relationships, development of new skills unrelated to the problem, and using problematic experience as a resource for new situations.",
        "contents-zh": "关注新项目,关注新关系,发展新技能,将问题经验作为新情况下的资源.",
        "example": "Client: 'I want to do all the things that were impossible for me to do while I was dominated by depression.'",
        "chinese_example": "来访者:'我计划下个月去旅行,认识新朋友. '"
    },
    {
        "name": "Reflection II",
        "definition": "Contrasting self (what changed?) or self-transformation (how/why change occurred?).",
        "definition-zh": "对比自我（什么改变了？）或自我转变（如何/为什么变化发生了？）. ",
        "contents": "Contrasting self-positions across time, (ongoing) resolution of past internal or relational conflict, moments of self-observation and realization of progress relative to new changes, and references to improved well-being or self-worth due to changes.",
        "contents-zh": "对比自我在时间上的变化,解决过去内部或关系冲突,自我观察和意识到进步,以及由于变化而改善的自我价值或/和良好的感受.",
        "example": "Client: 'I believe that our talks, our sessions, have proven fruitful.'",
        "chinese_example": "来访者:'现在回头看,我已经不像以前那样容易崩溃了. '"
    },
    {
        "name": "Protest II",
        "definition": "Assertiveness and empowerment.",
        "definition-zh": "自我肯定与赋权. ",
        "contents": "Centering on the self, affirming personal rights, needs, and values, including references to self-worth, feelings of well-being, and the ability to make choices.",   
        "contents-zh": "关注自我,肯定个人权利,需求和价值观,包括自我价值,良好感受和做出选择的能力.",
        "example": "Client: 'I'm feeling stronger now, and won't let depression rule my life anymore!'",
        "chinese_example": "来访者:'我有权利追求自己的幸福,不再被过去束缚！'"
    }
]
# 英文版IMCS类别定义
IMCS_CATEGORIES_en = [
    {
        "name": "Action I",
        "definition": "Performed and intended actions to overcome the problem.",
        "contents": "New behavioral strategies to overcome the problem, active exploration of solutions, and searching for information about the problem.",
        "example": "Client: 'Yesterday, I went to the cinema for the first time in months!'"
    },
    {
        "name": "Reflection I",
        "definition": "New understanding or rethinking of the problem.",
        "contents": "Reconsidering the problem's causes, awareness of its effects, new problem formulations, adaptive self-instructions and thoughts, intention to fight (CONTEST) the problem's demands, and references to self-worth and/or feelings of well-being.",
        "example": "Client: 'I realize that the more I isolate myself, the more depression gets overwhelming...'"
    },
    {
        "name": "Protest I",
        "definition": "Objecting to the problem and its assumptions.",
        "contents": "Rejecting or objecting to the problem, critique of those who support it, and critique of problematic facets of the self.",
        "example": "Client: 'I won't let my fear of others destroy my life.'"
    },
    {
        "name": "Action II",    
        "definition": "Generalization into the future and other life dimensions of good outcomes (performed or projected actions).",
        "contents": "Investment in new projects, investment in new relationships, development of new skills unrelated to the problem, and using problematic experience as a resource for new situations.",
        "example": "Client: 'I want to do all the things that were impossible for me to do while I was dominated by depression.'"
    },
    {
        "name": "Reflection II",
        "definition": "Contrasting self (what changed?) or self-transformation (how/why change occurred?).",
        "contents": "Contrasting self-positions across time, (ongoing) resolution of past internal or relational conflict, moments of self-observation and realization of progress relative to new changes, and references to improved well-being or self-worth due to changes.",
        "example": "Client: 'I believe that our talks, our sessions, have proven fruitful.'"
    },
    {
        "name": "Protest II",
        "definition": "Assertiveness and empowerment.",
        "contents": "Centering on the self, affirming personal rights, needs, and values, including references to self-worth, feelings of well-being, and the ability to make choices.",   
        "example": "Client: 'I'm feeling stronger now, and won't let depression rule my life anymore!'"
    }
]
