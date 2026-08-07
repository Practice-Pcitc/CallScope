# Java Spring 支持说明

## 支持范围

CallScope 会自动发现 `.java` 文件；当 Java 文件数量不少于 Python 文件时，将项目
识别为 `java / spring`，不需要用户手动选择语言。

当前支持：

- `@RestController` 与 `@Controller`；
- 类级 `@RequestMapping`；
- `@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`、
  `@PatchMapping`；
- 指定 `RequestMethod` 的方法级 `@RequestMapping`；
- `@PathVariable`、`@RequestParam`、`@RequestBody`、`@RequestHeader`、
  `@CookieValue`、`@RequestPart` 和 `@ModelAttribute`；
- Controller、Service、Component、Repository、Mapper 方法节点；
- 根据 Controller 类注释或类名生成业务分类并在接口列表中分组；
- 构造器注入字段、`@Resource`/`@Autowired` 字段的静态类型解析；
- 接口类型到常见 `*Impl` 实现类的静态解析；
- 方法调用关系、文件位置、行号、源码片段和置信度。
- 默认加载五层调用关系，并为接口与方法生成静态业务逻辑摘要和处理步骤。

## 安全性

扫描过程只读取源码，不执行 Maven/Gradle，不编译 Java，不启动 Spring，也不会
安装目标项目依赖。源码读取优先尝试 UTF-8，必要时回退到 GB18030。

## 已验证项目

`DrawingSystem-Cloud-Api-main` 的验收结果：

- Java 文件：300；
- Spring HTTP 接口：98；
- 扫描失败文件：0；
- 可解析 `API → ROUTE_FUNCTION → SERVICE`；
- 已识别 31 条 `SERVICE → REPOSITORY` 关系。

## 已知边界

Java 静态分析不等价于编译器。重载消歧、Spring 运行时代理、反射、动态 Bean
查找、跨依赖源码和复杂链式泛型调用可能无法完整解析。无法确认的调用不会被伪装
为确定关系。
