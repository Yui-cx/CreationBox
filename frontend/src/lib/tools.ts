import { ToolConfig } from "../types";

export const tools: Record<string, ToolConfig> = {
  humanize: {
    id: "humanize",
    title: "AI痕迹去除",
    kicker: "自然表达优化",
    tag: "默认",
    description: "将机械、模板化表达优化成更自然、有节奏的公众号文字，不承诺检测规避结果。",
    modes: [
      { id: "quick", label: "极速模式", limit: 600 },
      { id: "long", label: "长文本模式", limit: 2500 }
    ],
    generateLabel: "开始优化",
    sourceLabel: "输入内容",
    sourceHelper: "极速模式最多 600 字，长文本模式最多 2500 字。",
    textPlaceholder: "输入需要优化自然表达的公众号段落。",
    styles: ["默认"],
    tones: ["默认"],
    examples: [
      "随着消费环境的持续变化，品牌需要通过系统化的方法提升用户粘性，并在长期运营中形成稳定的复购机制。",
      "本文将从内容定位、用户分层和社群运营三个方面进行分析，帮助商家建立更具持续性的增长路径。"
    ]
  },
  aigc_reduce: {
    id: "aigc_reduce",
    title: "降AIGC率",
    kicker: "文本表达降重",
    tag: "降AIGC",
    description: "在不承诺检测结果的前提下，调整文本语序、词汇和句式，让表达更平实普通。",
    modes: [
      { id: "text", label: "文本输入", limit: 1500 }
    ],
    generateLabel: "开始处理",
    sourceLabel: "输入内容",
    sourceHelper: "输入文本最多 1500 字，文件读取即将支持 markdown、txt、word。",
    textPlaceholder: "输入需要处理的论文段落或正文内容。",
    styles: ["默认"],
    tones: ["默认"],
    examples: [
      "随着数字化技术的不断发展，企业管理模式正在发生深刻变化，这种变化不仅提升了组织运行效率，也为后续创新提供了重要基础。",
      "本文通过分析相关案例，探讨该方法在实际应用中的作用，并进一步说明其对行业发展的影响。"
    ]
  },
  generate: {
    id: "generate",
    title: "生成文章",
    kicker: "公众号草稿生成",
    tag: "生成",
    description: "输入主题或参考链接，快速生成公众号文章草稿，适合选题验证和初稿搭建。",
    modes: [
      { id: "topic", label: "主题生成" },
      { id: "link", label: "参考链接" }
    ],
    generateLabel: "生成文章",
    sourceLabel: "补充素材",
    sourceHelper: "可填写产品卖点、案例、门店信息或其他素材。",
    textPlaceholder: "补充文章素材，例如品牌背景、案例、关键数据。",
    linkPlaceholder: "https://news.example.com/article\nhttps://mp.weixin.qq.com/s/example",
    linkHelper: "可填写多个参考链接，建议每行一个；首版不抓取真实网页，链接会作为参考素材发送给模型。",
    styleLabel: "内容类型",
    toneLabel: "文章语气",
    styles: ["行业观察", "运营方法论", "品牌故事", "活动推文", "产品种草", "自定义"],
    tones: ["专业可信", "轻松亲切", "克制高级", "热情直接", "故事感", "自定义"],
    examples: [
      "本地咖啡品牌如何用社群提升复购",
      "面向私域运营者，写一篇关于公众号内容规划的文章"
    ]
  }
};
